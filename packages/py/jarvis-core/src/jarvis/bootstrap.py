from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from jarvis.identity.models import Permission, Role, RolePermission
from jarvis.knowledge.models import (
    Resource,
    ResourceNamespace,
    ResourceRevision,
    ResourceType,
)
from jarvis.platform.manifest import load_example_manifest
from jarvis.platform.service import register_manifest

CORE_PERMISSIONS: dict[str, str] = {
    "workspace.read": "Read workspace metadata.",
    "workspace.manage": "Create and manage workspaces.",
    "resource.read": "Read system and permitted private resources.",
    "resource.write": "Create and update private resources.",
    "module.read": "Read trusted module catalog and installations.",
    "module.manage": "Install, enable, disable, and remove modules.",
    "configuration.read": "Export workspace configuration.",
    "configuration.write": "Import workspace configuration.",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": set(CORE_PERMISSIONS),
    "admin": set(CORE_PERMISSIONS),
    "editor": {
        "workspace.read",
        "resource.read",
        "resource.write",
        "module.read",
        "configuration.read",
    },
    "viewer": {
        "workspace.read",
        "resource.read",
        "module.read",
        "configuration.read",
    },
}


def bootstrap_foundation(session: Session) -> None:
    permissions: dict[str, Permission] = {}
    for key, description in CORE_PERMISSIONS.items():
        permission = session.scalar(select(Permission).where(Permission.key == key))
        if permission is None:
            permission = Permission(key=key, description=description)
            session.add(permission)
            session.flush()
        permissions[key] = permission

    roles: dict[str, Role] = {}
    for key in ("owner", "admin", "editor", "viewer"):
        role = session.scalar(select(Role).where(Role.key == key))
        if role is None:
            role = Role(
                key=key,
                name=key.title(),
                description=f"Built-in {key} role.",
            )
            session.add(role)
            session.flush()
        roles[key] = role

    for role_key, permission_keys in ROLE_PERMISSIONS.items():
        role = roles[role_key]
        for permission_key in permission_keys:
            permission = permissions[permission_key]
            if (
                session.get(
                    RolePermission,
                    {"role_id": role.id, "permission_id": permission.id},
                )
                is None
            ):
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    resource_type = session.scalar(
        select(ResourceType).where(ResourceType.key == "foundation_record")
    )
    if resource_type is None:
        resource_type = ResourceType(
            key="foundation_record",
            name="Foundation Record",
            module_key="jarvis.core",
        )
        session.add(resource_type)
        session.flush()

    namespace = session.scalar(
        select(ResourceNamespace).where(
            ResourceNamespace.kind == "system",
            ResourceNamespace.key == "system.core",
        )
    )
    if namespace is None:
        namespace = ResourceNamespace(
            workspace_id=None,
            key="system.core",
            name="JARVIS System Catalog",
            kind="system",
            read_only=True,
            is_default=True,
        )
        session.add(namespace)
        session.flush()

    resource = session.scalar(
        select(Resource).where(
            Resource.namespace_id == namespace.id,
            Resource.slug == "platform-foundation",
        )
    )
    if resource is None:
        now = datetime.now(UTC)
        payload: dict[str, object] = {
            "summary": "Shared system resource proving the catalog boundary."
        }
        resource = Resource(
            resource_type_id=resource_type.id,
            namespace_id=namespace.id,
            scope="system",
            workspace_id=None,
            slug="platform-foundation",
            title="Platform Foundation",
            lifecycle_status="active",
            lock_version=1,
            created_by_user_id=None,
        )
        session.add(resource)
        session.flush()
        canonical = json.dumps(
            {"title": resource.title, "payload": payload},
            sort_keys=True,
            separators=(",", ":"),
        )
        revision = ResourceRevision(
            resource_id=resource.id,
            workspace_id=None,
            scope="system",
            revision_number=1,
            content_hash=hashlib.sha256(canonical.encode()).hexdigest(),
            payload=payload,
            authority="system",
            confidence=Decimal("1"),
            source_status="system",
            created_by_user_id=None,
            created_at=now,
            published_at=now,
        )
        session.add(revision)
        session.flush()
        resource.current_revision_id = revision.id

    register_manifest(session, load_example_manifest())
