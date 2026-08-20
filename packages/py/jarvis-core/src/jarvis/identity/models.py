from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from jarvis.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="valid_status"),
        {"schema": "identity"},
    )

    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    primary_email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthIdentity(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="issuer_subject"),
        {"schema": "identity"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    last_authenticated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("token_digest", name="token_digest"),
        Index(
            "ix_sessions_active_expiry",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        {"schema": "identity"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    digest_key_version: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auth_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mfa_context: Mapped[str | None] = mapped_column(String(200))


class OIDCLoginTransaction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "oidc_login_transactions"
    __table_args__ = (
        UniqueConstraint("state_digest", name="state_digest"),
        {"schema": "identity"},
    )

    issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    state_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    binding_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    verifier_ciphertext: Mapped[str] = mapped_column(nullable=False)
    nonce_ciphertext: Mapped[str] = mapped_column(nullable=False)
    return_path: Mapped[str] = mapped_column(String(500), nullable=False, default="/")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Role(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "roles"
    __table_args__ = ({"schema": "identity"},)

    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")


class Permission(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "permissions"
    __table_args__ = ({"schema": "identity"},)

    key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = ({"schema": "identity"},)

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("kind IN ('personal', 'team')", name="valid_kind"),
        CheckConstraint("status IN ('active', 'archived')", name="valid_status"),
        {"schema": "identity"},
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="personal")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=False,
    )


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'suspended')", name="valid_status"),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["identity.workspaces.id"],
            ondelete="CASCADE",
        ),
        {"schema": "identity"},
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.roles.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
