from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from jarvis.core.errors import ConflictError, NotFoundError, PreconditionFailedError
from jarvis.core.serialization import CursorCodec, PageInfo
from jarvis.knowledge.models import (
    Resource,
    ResourceNamespace,
    ResourceRevision,
    ResourceType,
)
from jarvis.knowledge.schemas import ResourceCreate, ResourcePage, ResourceRead, ResourceUpdate

ResourceRow = Row[tuple[Resource, str, str, int, Decimal | None]]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _content_hash(title: str, payload: dict[str, object]) -> str:
    canonical = json.dumps(
        {"title": title, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_workspace_namespace(
    session: Session,
    *,
    workspace_id: UUID,
    workspace_slug: str,
    workspace_name: str,
) -> ResourceNamespace:
    namespace = ResourceNamespace(
        workspace_id=workspace_id,
        key=f"workspace.{workspace_slug}",
        name=f"{workspace_name} Knowledge",
        kind="workspace",
        read_only=False,
        is_default=True,
    )
    session.add(namespace)
    session.flush()
    return namespace


def _resource_row(
    resource_id: UUID,
) -> Select[tuple[Resource, str, str, int, Decimal | None]]:
    return (
        select(
            Resource,
            ResourceType.key.label("type_key"),
            ResourceNamespace.key.label("namespace_key"),
            ResourceRevision.revision_number,
            ResourceRevision.confidence,
        )
        .join(ResourceType, ResourceType.id == Resource.resource_type_id)
        .join(ResourceNamespace, ResourceNamespace.id == Resource.namespace_id)
        .outerjoin(ResourceRevision, ResourceRevision.id == Resource.current_revision_id)
        .where(Resource.id == resource_id)
    )


def _to_read(row: ResourceRow) -> ResourceRead:
    resource = row[0]
    type_key = row[1]
    namespace_key = row[2]
    revision_number = row[3]
    confidence = row[4]
    return ResourceRead(
        id=resource.id,
        type_key=type_key,
        namespace_key=namespace_key,
        scope=resource.scope,
        workspace_id=resource.workspace_id,
        slug=resource.slug,
        title=resource.title,
        lifecycle_status=resource.lifecycle_status,
        lock_version=resource.lock_version,
        current_revision_id=resource.current_revision_id,
        revision_number=revision_number,
        confidence=confidence,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


def get_resource(session: Session, resource_id: UUID) -> ResourceRead:
    row = session.execute(_resource_row(resource_id)).one_or_none()
    if row is None:
        raise NotFoundError("Resource not found.")
    return _to_read(row)


def list_resources(
    session: Session,
    *,
    codec: CursorCodec,
    cursor: str | None,
    limit: int,
) -> ResourcePage:
    statement = (
        select(
            Resource,
            ResourceType.key.label("type_key"),
            ResourceNamespace.key.label("namespace_key"),
            ResourceRevision.revision_number,
            ResourceRevision.confidence,
        )
        .join(ResourceType, ResourceType.id == Resource.resource_type_id)
        .join(ResourceNamespace, ResourceNamespace.id == Resource.namespace_id)
        .outerjoin(ResourceRevision, ResourceRevision.id == Resource.current_revision_id)
        .where(Resource.lifecycle_status != "deleted")
        .order_by(Resource.created_at, Resource.id)
    )
    if cursor:
        value = codec.decode(cursor)
        cursor_created_at = datetime.fromisoformat(str(value["created_at"]))
        cursor_id = UUID(str(value["id"]))
        statement = statement.where(
            or_(
                Resource.created_at > cursor_created_at,
                and_(
                    Resource.created_at == cursor_created_at,
                    Resource.id > cursor_id,
                ),
            )
        )
    rows = session.execute(statement.limit(limit + 1)).all()
    has_more = len(rows) > limit
    visible = rows[:limit]
    next_cursor = None
    if has_more and visible:
        last = visible[-1][0]
        next_cursor = codec.encode(
            {
                "created_at": last.created_at.isoformat(),
                "id": str(last.id),
            }
        )
    return ResourcePage(
        items=[_to_read(row) for row in visible],
        page=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


def create_workspace_resource(
    session: Session,
    *,
    workspace_id: UUID,
    actor_id: UUID,
    data: ResourceCreate,
) -> ResourceRead:
    namespace = session.scalar(
        select(ResourceNamespace).where(
            ResourceNamespace.workspace_id == workspace_id,
            ResourceNamespace.kind == "workspace",
            ResourceNamespace.is_default.is_(True),
        )
    )
    if namespace is None:
        raise RuntimeError("Workspace default namespace is missing")
    resource_type = session.scalar(select(ResourceType).where(ResourceType.key == data.type_key))
    if resource_type is None:
        raise NotFoundError("Resource type not found.")
    duplicate = session.scalar(
        select(Resource.id).where(
            Resource.namespace_id == namespace.id,
            Resource.slug == data.slug,
        )
    )
    if duplicate:
        raise ConflictError("A resource with this slug already exists in the namespace.")

    now = _utc_now()
    resource = Resource(
        resource_type_id=resource_type.id,
        namespace_id=namespace.id,
        scope="workspace",
        workspace_id=workspace_id,
        slug=data.slug,
        title=data.title,
        lifecycle_status="active",
        lock_version=1,
        created_by_user_id=actor_id,
    )
    session.add(resource)
    session.flush()
    revision = ResourceRevision(
        resource_id=resource.id,
        workspace_id=workspace_id,
        scope="workspace",
        revision_number=1,
        content_hash=_content_hash(data.title, data.payload),
        payload=data.payload,
        authority="user",
        confidence=Decimal(data.confidence) if data.confidence is not None else None,
        source_status="user",
        created_by_user_id=actor_id,
        created_at=now,
        published_at=now,
    )
    session.add(revision)
    session.flush()
    resource.current_revision_id = revision.id
    session.flush()
    return get_resource(session, resource.id)


def update_resource(
    session: Session,
    *,
    resource_id: UUID,
    expected_lock_version: int,
    data: ResourceUpdate,
) -> ResourceRead:
    resource = session.scalar(select(Resource).where(Resource.id == resource_id).with_for_update())
    if resource is None:
        raise NotFoundError("Resource not found.")
    if resource.lock_version != expected_lock_version:
        raise PreconditionFailedError()

    values: dict[str, object] = {
        "lock_version": Resource.lock_version + 1,
        "updated_at": func.now(),
    }
    if data.lifecycle_status is not None:
        values["lifecycle_status"] = data.lifecycle_status
    if data.title is not None and data.title != resource.title:
        current_revision = session.get(ResourceRevision, resource.current_revision_id)
        if current_revision is None:
            raise RuntimeError("Resource current revision is missing")
        new_revision = ResourceRevision(
            resource_id=resource.id,
            workspace_id=resource.workspace_id,
            scope=resource.scope,
            revision_number=current_revision.revision_number + 1,
            content_hash=_content_hash(data.title, current_revision.payload),
            payload=current_revision.payload,
            authority=current_revision.authority,
            confidence=current_revision.confidence,
            source_status=current_revision.source_status,
            created_by_user_id=resource.created_by_user_id,
            created_at=_utc_now(),
            published_at=_utc_now(),
            supersedes_revision_id=current_revision.id,
        )
        session.add(new_revision)
        session.flush()
        values["title"] = data.title
        values["current_revision_id"] = new_revision.id

    updated_id = session.scalar(
        update(Resource)
        .where(
            Resource.id == resource_id,
            Resource.lock_version == expected_lock_version,
        )
        .values(**values)
        .returning(Resource.id)
    )
    if updated_id is None:
        raise PreconditionFailedError()
    session.expire_all()
    return get_resource(session, updated_id)
