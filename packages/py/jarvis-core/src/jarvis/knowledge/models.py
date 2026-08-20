from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from jarvis.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResourceNamespace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resource_namespaces"
    __table_args__ = (
        CheckConstraint("kind IN ('system', 'workspace')", name="valid_kind"),
        CheckConstraint(
            "(kind = 'system' AND workspace_id IS NULL) OR "
            "(kind = 'workspace' AND workspace_id IS NOT NULL)",
            name="workspace_scope",
        ),
        UniqueConstraint(
            "workspace_id",
            "key",
            name="uq_resource_namespaces_workspace_key",
        ),
        UniqueConstraint(
            "id",
            "workspace_id",
            name="uq_resource_namespaces_id_workspace",
        ),
        Index(
            "uq_resource_namespaces_system_key",
            "key",
            unique=True,
            postgresql_where=text("kind = 'system'"),
        ),
        Index(
            "uq_resource_namespaces_default_workspace",
            "workspace_id",
            unique=True,
            postgresql_where=text("kind = 'workspace' AND is_default"),
        ),
        {"schema": "knowledge"},
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    key: Mapped[str] = mapped_column(String(150), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ResourceType(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "resource_types"
    __table_args__ = ({"schema": "knowledge"},)

    key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    module_key: Mapped[str] = mapped_column(String(150), nullable=False)


class Resource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint("scope IN ('system', 'workspace')", name="valid_scope"),
        CheckConstraint(
            "(scope = 'system' AND workspace_id IS NULL) OR "
            "(scope = 'workspace' AND workspace_id IS NOT NULL)",
            name="workspace_scope",
        ),
        CheckConstraint(
            "lifecycle_status IN ('active', 'archived', 'deleted')",
            name="valid_lifecycle_status",
        ),
        UniqueConstraint("id", "workspace_id", name="uq_resources_id_workspace"),
        UniqueConstraint(
            "namespace_id",
            "slug",
            name="uq_resources_namespace_slug",
        ),
        ForeignKeyConstraint(
            ["namespace_id", "workspace_id"],
            ["knowledge.resource_namespaces.id", "knowledge.resource_namespaces.workspace_id"],
            name="namespace_workspace",
        ),
        ForeignKeyConstraint(
            ["current_revision_id", "id"],
            ["knowledge.resource_revisions.id", "knowledge.resource_revisions.resource_id"],
            name="fk_resources_current_revision",
            use_alter=True,
        ),
        {"schema": "knowledge"},
    )

    resource_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge.resource_types.id"),
        nullable=False,
        index=True,
    )
    namespace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge.resource_namespaces.id"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
    )


class ResourceRevision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "resource_revisions"
    __table_args__ = (
        CheckConstraint("scope IN ('system', 'workspace')", name="valid_scope"),
        CheckConstraint(
            "(scope = 'system' AND workspace_id IS NULL) OR "
            "(scope = 'workspace' AND workspace_id IS NOT NULL)",
            name="workspace_scope",
        ),
        UniqueConstraint(
            "resource_id",
            "revision_number",
            name="uq_resource_revisions_resource_number",
        ),
        UniqueConstraint(
            "id",
            "resource_id",
            name="uq_resource_revisions_id_resource",
        ),
        ForeignKeyConstraint(
            ["resource_id", "workspace_id"],
            ["knowledge.resources.id", "knowledge.resources.workspace_id"],
            name="resource_workspace",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["supersedes_revision_id", "resource_id"],
            ["knowledge.resource_revisions.id", "knowledge.resource_revisions.resource_id"],
            name="fk_resource_revisions_supersedes_same_resource",
            use_alter=True,
        ),
        {"schema": "knowledge"},
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge.resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    authority: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))
    source_status: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge.resource_revisions.id"),
    )


class ResourceRevisionLifecycleEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "resource_revision_lifecycle_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('superseded', 'deprecated', 'withdrawn', 'restored')",
            name="valid_event_type",
        ),
        {"schema": "knowledge"},
    )

    resource_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge.resource_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
