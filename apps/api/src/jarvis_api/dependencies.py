from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, Request, Security
from fastapi.security import APIKeyCookie
from jarvis.core.errors import AuthenticationError, AuthorizationError
from jarvis.core.security import TokenSecurity
from jarvis.core.serialization import CursorCodec
from jarvis.core.settings import Settings
from jarvis.db.session import (
    assume_application_role,
    set_actor_context,
    set_workspace_context,
)
from jarvis.identity.schemas import Principal
from jarvis.identity.service import get_workspace, require_permission, resolve_session
from sqlalchemy.orm import Session

session_cookie_scheme = APIKeyCookie(
    name="__Host-jarvis_session",
    auto_error=False,
    description="Opaque server-side JARVIS session cookie.",
)


@dataclass(slots=True)
class ApplicationServices:
    settings: Settings
    security: TokenSecurity
    cursor_codec: CursorCodec


def get_services(request: Request) -> ApplicationServices:
    return request.app.state.services


def get_db(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.session_factory()
    try:
        with session.begin():
            assume_application_role(session)
            yield session
    finally:
        session.close()


def get_principal(
    request: Request,
    db: Session = Depends(get_db),
    services: ApplicationServices = Depends(get_services),
    documented_cookie: str | None = Security(session_cookie_scheme),
) -> Principal:
    raw_token = documented_cookie or request.cookies.get(
        services.settings.effective_session_cookie_name
    )
    if not raw_token:
        raise AuthenticationError()
    principal = resolve_session(db, raw_token=raw_token, security=services.security)
    if principal is None:
        raise AuthenticationError("The session is invalid or expired.")
    set_actor_context(db, principal.user_id, principal.session_id)
    return principal


def require_csrf(
    x_csrf_token: str = Header(alias="X-CSRF-Token"),
    principal: Principal = Depends(get_principal),
    services: ApplicationServices = Depends(get_services),
) -> None:
    expected = services.security.csrf_token(principal.session_id)
    if not services.security.verify_digest(
        x_csrf_token,
        services.security.digest(expected, purpose="csrf-comparison"),
        purpose="csrf-comparison",
    ):
        raise AuthorizationError("The CSRF token is missing or invalid.")


def workspace_scope(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> UUID:
    set_workspace_context(db, workspace_id)
    require_permission(
        db,
        user_id=principal.user_id,
        workspace_id=workspace_id,
        permission_key="workspace.read",
    )
    get_workspace(db, workspace_id)
    return workspace_id


def permission(permission_key: str):
    def dependency(
        workspace_id: UUID = Depends(workspace_scope),
        db: Session = Depends(get_db),
        principal: Principal = Depends(get_principal),
    ) -> None:
        require_permission(
            db,
            user_id=principal.user_id,
            workspace_id=workspace_id,
            permission_key=permission_key,
        )

    return dependency
