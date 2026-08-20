from __future__ import annotations

from typing import cast
from urllib.parse import urljoin
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from jarvis.core.errors import AuthenticationError, NotFoundError
from jarvis.db.session import (
    assume_application_role,
    session_scope,
    set_workspace_context,
)
from jarvis.governance.service import record_change
from jarvis.identity.models import User, WorkspaceMembership
from jarvis.identity.oidc import OIDCService
from jarvis.identity.schemas import Principal, SessionRead, UserRead, WorkspaceCreate
from jarvis.identity.service import create_workspace, revoke_session
from jarvis.knowledge.service import create_workspace_namespace
from jarvis.platform.models import WorkspacePreferences
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from jarvis_api.dependencies import (
    ApplicationServices,
    get_db,
    get_principal,
    get_services,
    require_csrf,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get(
    "/login",
    status_code=302,
    response_class=RedirectResponse,
    responses={302: {"description": "Redirect to the configured OIDC provider."}},
)
def login(
    return_path: str = Query(default="/"),
    db: Session = Depends(get_db),
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    result = OIDCService(services.settings, services.security).start_login(
        db,
        return_path=return_path,
    )
    response = RedirectResponse(result.authorization_url, status_code=302)
    response.set_cookie(
        key=services.settings.effective_oidc_binding_cookie_name,
        value=result.binding_token,
        secure=services.settings.secure_cookies,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=600,
    )
    return response


@router.get(
    "/callback",
    status_code=302,
    response_class=RedirectResponse,
    responses={302: {"description": "OIDC login completed; redirect to the workstation."}},
)
def callback(
    state: str,
    code: str,
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    oidc = OIDCService(services.settings, services.security)
    factory = cast(sessionmaker[Session], request.app.state.session_factory)
    binding_token = request.cookies.get(services.settings.effective_oidc_binding_cookie_name)
    if not binding_token:
        raise AuthenticationError("OIDC browser binding is missing.")
    with session_scope(factory) as consume_session:
        assume_application_role(consume_session)
        consumed = oidc.consume_login(
            consume_session,
            state=state,
            binding_token=binding_token,
        )
    identity = oidc.validate_login(consumed=consumed, code=code)
    with session_scope(factory) as finish_session:
        assume_application_role(finish_session)
        result = oidc.finish_login(
            finish_session,
            identity=identity,
        )
        ensure_personal_workspace(
            finish_session,
            user_id=result.user_id,
            request_id=request.state.request_id,
        )
    response = RedirectResponse(
        url=urljoin(services.settings.web_origin, result.return_path),
        status_code=302,
    )
    response.set_cookie(
        key=services.settings.effective_session_cookie_name,
        value=result.raw_session_token,
        secure=services.settings.secure_cookies,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=services.settings.session_ttl_seconds,
    )
    response.delete_cookie(
        services.settings.effective_oidc_binding_cookie_name,
        path="/",
        secure=services.settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    return response


def ensure_personal_workspace(
    session: Session,
    *,
    user_id: UUID,
    request_id: str,
) -> None:
    membership = session.scalar(
        select(WorkspaceMembership.workspace_id).where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if membership is not None:
        return
    slug = f"personal-{user_id.hex}"
    workspace = create_workspace(
        session,
        actor_id=user_id,
        data=WorkspaceCreate(name="Personal Workspace", slug=slug, kind="personal"),
    )
    set_workspace_context(session, workspace.id)
    create_workspace_namespace(
        session,
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        workspace_name=workspace.name,
    )
    session.add(WorkspacePreferences(workspace_id=workspace.id, values={}, lock_version=1))
    record_change(
        session,
        workspace_id=workspace.id,
        actor_user_id=user_id,
        action="workspace.bootstrap",
        resource_type="workspace",
        resource_id=workspace.id,
        event_type="identity.personal_workspace_created.v1",
        before=None,
        after={"name": workspace.name, "slug": workspace.slug, "kind": workspace.kind},
        request_id=request_id,
    )


@router.get("/session", response_model=SessionRead)
def session_status(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
    services: ApplicationServices = Depends(get_services),
) -> SessionRead:
    user = db.get(User, principal.user_id)
    if user is None:
        raise NotFoundError("Authenticated user was not found.")
    return SessionRead(
        authenticated=True,
        user=UserRead.model_validate(user),
        csrf_token=services.security.csrf_token(principal.session_id),
    )


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf)])
def logout(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    services: ApplicationServices = Depends(get_services),
) -> Response:
    revoke_session(db, session_id=principal.session_id)
    response = Response(status_code=204)
    response.delete_cookie(
        services.settings.effective_session_cookie_name,
        path="/",
        secure=services.settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    return response
