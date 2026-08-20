from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from jarvis.db.session import set_workspace_context
from jarvis.governance.service import record_change
from jarvis.identity.models import User
from jarvis.identity.schemas import (
    CurrentUserRead,
    MembershipRead,
    Principal,
    UserRead,
    WorkspaceCreate,
    WorkspaceRead,
)
from jarvis.identity.service import (
    create_workspace,
    get_workspace,
    list_workspaces,
    membership_query,
)
from jarvis.knowledge.service import create_workspace_namespace
from jarvis.platform.models import WorkspacePreferences
from sqlalchemy.orm import Session

from jarvis_api.dependencies import (
    get_db,
    get_principal,
    require_csrf,
    workspace_scope,
)

router = APIRouter(tags=["identity"])


@router.get("/me", response_model=CurrentUserRead)
def me(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> CurrentUserRead:
    user = db.get(User, principal.user_id)
    if user is None:
        raise RuntimeError("Authenticated user is missing")
    memberships = [
        MembershipRead(
            workspace_id=membership.workspace_id,
            user_id=membership.user_id,
            role_key=role.key,
            status=membership.status,
        )
        for membership, role in db.execute(membership_query(principal.user_id)).all()
    ]
    return CurrentUserRead(user=UserRead.model_validate(user), memberships=memberships)


@router.get("/workspaces", response_model=list[WorkspaceRead])
def workspaces(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
) -> list[WorkspaceRead]:
    return [WorkspaceRead.model_validate(item) for item in list_workspaces(db)]


@router.post(
    "/workspaces",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_new_workspace(
    data: WorkspaceCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> WorkspaceRead:
    workspace = create_workspace(db, actor_id=principal.user_id, data=data)
    set_workspace_context(db, workspace.id)
    create_workspace_namespace(
        db,
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        workspace_name=workspace.name,
    )
    db.add(WorkspacePreferences(workspace_id=workspace.id, values={}, lock_version=1))
    record_change(
        db,
        workspace_id=workspace.id,
        actor_user_id=principal.user_id,
        action="workspace.create",
        resource_type="workspace",
        resource_id=workspace.id,
        event_type="identity.workspace_created.v1",
        before=None,
        after={"name": workspace.name, "slug": workspace.slug, "kind": workspace.kind},
        request_id=request.state.request_id,
    )
    db.flush()
    return WorkspaceRead.model_validate(workspace)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceRead)
def workspace(
    workspace_id: UUID = Depends(workspace_scope),
    db: Session = Depends(get_db),
) -> WorkspaceRead:
    return WorkspaceRead.model_validate(get_workspace(db, workspace_id))
