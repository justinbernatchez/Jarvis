from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, select, text, update
from sqlalchemy.orm import Session

from jarvis.core.errors import AuthorizationError, ConflictError, NotFoundError
from jarvis.core.security import TokenSecurity
from jarvis.core.settings import Settings
from jarvis.identity.models import (
    AuthIdentity,
    Permission,
    Role,
    RolePermission,
    User,
    UserSession,
    Workspace,
    WorkspaceMembership,
)
from jarvis.identity.schemas import Principal, WorkspaceCreate


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_user_with_identity(
    session: Session,
    *,
    issuer: str,
    subject: str,
    email: str,
    display_name: str,
) -> User:
    existing = session.scalar(
        select(AuthIdentity).where(
            AuthIdentity.issuer == issuer,
            AuthIdentity.subject == subject,
        )
    )
    if existing:
        user = session.get(User, existing.user_id)
        if user is None:
            raise RuntimeError("Identity points to a missing user")
        existing.last_authenticated_at = utc_now()
        return user

    user = User(display_name=display_name, primary_email=email, status="active")
    session.add(user)
    session.flush()
    session.add(
        AuthIdentity(
            user_id=user.id,
            issuer=issuer,
            subject=subject,
            last_authenticated_at=utc_now(),
        )
    )
    return user


def create_workspace(session: Session, *, actor_id: UUID, data: WorkspaceCreate) -> Workspace:
    if session.scalar(select(Workspace.id).where(Workspace.slug == data.slug)):
        raise ConflictError("A workspace with this slug already exists.")
    owner = session.scalar(select(Role).where(Role.key == "owner"))
    if owner is None:
        raise RuntimeError("Foundation roles have not been bootstrapped")

    workspace = Workspace(
        name=data.name,
        slug=data.slug,
        kind=data.kind,
        status="active",
        lock_version=1,
        created_by_user_id=actor_id,
    )
    session.add(workspace)
    session.flush()
    session.add(
        WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=actor_id,
            role_id=owner.id,
            status="active",
            joined_at=utc_now(),
        )
    )
    return workspace


def list_workspaces(session: Session) -> list[Workspace]:
    return list(session.scalars(select(Workspace).order_by(Workspace.created_at, Workspace.id)))


def get_workspace(session: Session, workspace_id: UUID) -> Workspace:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace not found.")
    return workspace


def membership_query(user_id: UUID) -> Select[tuple[WorkspaceMembership, Role]]:
    return (
        select(WorkspaceMembership, Role)
        .join(Role, Role.id == WorkspaceMembership.role_id)
        .where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.status == "active",
        )
    )


def require_permission(
    session: Session,
    *,
    user_id: UUID,
    workspace_id: UUID,
    permission_key: str,
) -> None:
    allowed = session.scalar(
        select(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(WorkspaceMembership, WorkspaceMembership.role_id == Role.id)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.status == "active",
            Permission.key == permission_key,
        )
        .limit(1)
    )
    if allowed is None:
        raise AuthorizationError()


def register_permissions(
    session: Session,
    permission_keys: list[str],
    *,
    grant_to_roles: tuple[str, ...] = ("owner", "admin"),
) -> None:
    roles = {
        role.key: role for role in session.scalars(select(Role).where(Role.key.in_(grant_to_roles)))
    }
    for key in permission_keys:
        permission = session.scalar(select(Permission).where(Permission.key == key))
        if permission is None:
            permission = Permission(key=key, description=f"Module permission: {key}")
            session.add(permission)
            session.flush()
        for role in roles.values():
            existing = session.get(
                RolePermission,
                {"role_id": role.id, "permission_id": permission.id},
            )
            if existing is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))


def issue_session(
    session: Session,
    *,
    user_id: UUID,
    settings: Settings,
    security: TokenSecurity,
    auth_time: datetime | None = None,
    mfa_context: str | None = None,
    rotate_existing: bool = False,
) -> tuple[UserSession, str]:
    raw_token = security.random_token()
    now = utc_now()
    if rotate_existing:
        session.execute(
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
    user_session = UserSession(
        user_id=user_id,
        token_digest=security.digest(raw_token, purpose="session"),
        digest_key_version=settings.session_hmac_key_version,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
        auth_time=auth_time or now,
        mfa_context=mfa_context,
    )
    session.add(user_session)
    session.flush()
    return user_session, raw_token


def resolve_session(
    session: Session,
    *,
    raw_token: str,
    security: TokenSecurity,
) -> Principal | None:
    token_digest = security.digest(raw_token, purpose="session")
    row = (
        session.execute(
            text(
                """
            SELECT session_id, user_id, auth_time
            FROM identity.resolve_session(:token_digest)
            """
            ),
            {"token_digest": token_digest},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    return Principal(
        user_id=row["user_id"],
        session_id=row["session_id"],
        auth_time=row["auth_time"],
    )


def revoke_session(session: Session, *, session_id: UUID) -> None:
    user_session = session.get(UserSession, session_id)
    if user_session is not None and user_session.revoked_at is None:
        user_session.revoked_at = utc_now()


def random_pkce_verifier() -> str:
    return secrets.token_urlsafe(64)
