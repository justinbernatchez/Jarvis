from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from jarvis.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Module(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "modules"
    __table_args__ = ({"schema": "platform"},)

    key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    lifecycle_status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")


class ModuleRelease(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "module_releases"
    __table_args__ = (
        UniqueConstraint("module_id", "semantic_version", name="module_version"),
        UniqueConstraint("id", "module_id", name="uq_module_releases_id_module"),
        UniqueConstraint(
            "id",
            "module_id",
            "semantic_version",
            name="uq_module_releases_id_module_version",
        ),
        {"schema": "platform"},
    )

    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform.modules.id", ondelete="CASCADE"),
        nullable=False,
    )
    semantic_version: Mapped[str] = mapped_column(String(50), nullable=False)
    manifest_version: Mapped[str] = mapped_column(String(20), nullable=False)
    core_compatibility: Mapped[str] = mapped_column(String(100), nullable=False)
    code_digest: Mapped[str] = mapped_column(String(100), nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration_schema: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    manifest: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Capability(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "capabilities"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('permission', 'route', 'component', 'provider', 'handler', 'ai_tool')",
            name="valid_kind",
        ),
        UniqueConstraint("id", "module_id", name="uq_capabilities_id_module"),
        {"schema": "platform"},
    )

    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform.modules.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)


class ModuleReleaseCapability(Base):
    __tablename__ = "module_release_capabilities"
    __table_args__ = (
        ForeignKeyConstraint(
            ["module_release_id", "module_id"],
            ["platform.module_releases.id", "platform.module_releases.module_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["capability_id", "module_id"],
            ["platform.capabilities.id", "platform.capabilities.module_id"],
            ondelete="CASCADE",
        ),
        {"schema": "platform"},
    )

    module_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    implementation_version: Mapped[str] = mapped_column(String(50), nullable=False)


class ModuleDependency(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "module_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "module_release_id",
            "target_module_id",
            name="release_target_module",
        ),
        UniqueConstraint(
            "id",
            "target_module_id",
            name="uq_module_dependencies_id_target",
        ),
        UniqueConstraint(
            "id",
            "target_module_id",
            "version_range",
            "module_release_id",
            name="uq_module_dependencies_resolution_identity",
        ),
        {"schema": "platform"},
    )

    module_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform.module_releases.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform.modules.id"),
        nullable=False,
    )
    version_range: Mapped[str] = mapped_column(String(100), nullable=False)


class ModuleInstallation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "module_installations"
    __table_args__ = (
        CheckConstraint("status IN ('installed', 'removed')", name="valid_status"),
        UniqueConstraint("workspace_id", "module_id", name="workspace_module"),
        UniqueConstraint(
            "id",
            "module_release_id",
            name="uq_module_installations_id_release",
        ),
        ForeignKeyConstraint(
            ["module_release_id", "module_id"],
            ["platform.module_releases.id", "platform.module_releases.module_id"],
        ),
        {"schema": "platform"},
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform.modules.id"),
        nullable=False,
    )
    module_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="installed")
    configuration: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    installed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=False,
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModuleDependencyResolution(Base):
    __tablename__ = "module_dependency_resolutions"
    __table_args__ = (
        CheckConstraint(
            "platform.semver_satisfies(resolved_version, version_range)",
            name="semver_range",
        ),
        ForeignKeyConstraint(
            [
                "dependency_id",
                "target_module_id",
                "version_range",
                "dependent_release_id",
            ],
            [
                "platform.module_dependencies.id",
                "platform.module_dependencies.target_module_id",
                "platform.module_dependencies.version_range",
                "platform.module_dependencies.module_release_id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["resolved_release_id", "target_module_id", "resolved_version"],
            [
                "platform.module_releases.id",
                "platform.module_releases.module_id",
                "platform.module_releases.semantic_version",
            ],
        ),
        ForeignKeyConstraint(
            ["installation_id", "dependent_release_id"],
            [
                "platform.module_installations.id",
                "platform.module_installations.module_release_id",
            ],
        ),
        {"schema": "platform"},
    )

    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform.module_installations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    dependency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    resolved_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    target_module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dependent_release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_range: Mapped[str] = mapped_column(String(100), nullable=False)
    resolved_version: Mapped[str] = mapped_column(String(50), nullable=False)


class NavigationNode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "navigation_nodes"
    __table_args__ = (
        UniqueConstraint("module_release_id", "key", name="release_key"),
        {"schema": "platform"},
    )

    module_release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform.module_releases.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_key: Mapped[str | None] = mapped_column(String(200))
    route_key: Mapped[str] = mapped_column(String(200), nullable=False)
    path: Mapped[str] = mapped_column(String(300), nullable=False)
    component_key: Mapped[str] = mapped_column(String(200), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    icon_key: Mapped[str] = mapped_column(String(100), nullable=False)
    default_order: Mapped[int] = mapped_column(Integer, nullable=False)
    required_permission: Mapped[str] = mapped_column(String(200), nullable=False)


class WorkspacePreferences(TimestampMixin, Base):
    __tablename__ = "workspace_preferences"
    __table_args__ = ({"schema": "platform"},)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    values: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    workflow_defaults: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    personal_categories: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class NavigationOverride(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "navigation_overrides"
    __table_args__ = (
        UniqueConstraint("workspace_id", "node_key", name="workspace_node"),
        {"schema": "platform"},
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_key: Mapped[str] = mapped_column(String(200), nullable=False)
    label: Mapped[str | None] = mapped_column(String(200))
    order: Mapped[int | None] = mapped_column(Integer)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
