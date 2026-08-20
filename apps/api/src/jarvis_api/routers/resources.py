from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from jarvis.core.errors import ApplicationError
from jarvis.governance.service import record_change
from jarvis.identity.schemas import Principal
from jarvis.knowledge.schemas import ResourceCreate, ResourcePage, ResourceRead, ResourceUpdate
from jarvis.knowledge.service import (
    create_workspace_resource,
    get_resource,
    list_resources,
    update_resource,
)
from sqlalchemy.orm import Session

from jarvis_api.dependencies import (
    ApplicationServices,
    get_db,
    get_principal,
    get_services,
    permission,
    require_csrf,
    workspace_scope,
)

router = APIRouter(tags=["resources"])
ETAG_HEADER = {
    "description": "Quoted optimistic lock version.",
    "schema": {"type": "string"},
}


@router.get("/catalog/resources", response_model=ResourcePage)
def catalog_resources(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
    services: ApplicationServices = Depends(get_services),
) -> ResourcePage:
    try:
        return list_resources(db, codec=services.cursor_codec, cursor=cursor, limit=limit)
    except ValueError as exc:
        raise ApplicationError(
            code="validation.cursor",
            title="Invalid cursor",
            status=422,
            detail="The pagination cursor is invalid.",
        ) from exc


@router.get(
    "/workspaces/{workspace_id}/resources",
    response_model=ResourcePage,
    dependencies=[Depends(workspace_scope), Depends(permission("resource.read"))],
)
def workspace_resources(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    services: ApplicationServices = Depends(get_services),
) -> ResourcePage:
    try:
        return list_resources(db, codec=services.cursor_codec, cursor=cursor, limit=limit)
    except ValueError as exc:
        raise ApplicationError(
            code="validation.cursor",
            title="Invalid cursor",
            status=422,
            detail="The pagination cursor is invalid.",
        ) from exc


@router.post(
    "/workspaces/{workspace_id}/resources",
    response_model=ResourceRead,
    status_code=status.HTTP_201_CREATED,
    responses={201: {"headers": {"ETag": ETAG_HEADER}}},
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("resource.write")),
        Depends(require_csrf),
    ],
)
def create_resource(
    workspace_id: UUID,
    data: ResourceCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ResourceRead:
    resource = create_workspace_resource(
        db,
        workspace_id=workspace_id,
        actor_id=principal.user_id,
        data=data,
    )
    record_change(
        db,
        workspace_id=workspace_id,
        actor_user_id=principal.user_id,
        action="resource.create",
        resource_type="resource",
        resource_id=resource.id,
        event_type="knowledge.resource_created.v1",
        before=None,
        after={
            "typeKey": resource.type_key,
            "slug": resource.slug,
            "title": resource.title,
        },
        request_id=request.state.request_id,
    )
    response.headers["ETag"] = f'"{resource.lock_version}"'
    return resource


@router.get(
    "/workspaces/{workspace_id}/resources/{resource_id}",
    response_model=ResourceRead,
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
    dependencies=[Depends(workspace_scope), Depends(permission("resource.read"))],
)
def read_resource(
    resource_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> ResourceRead:
    resource = get_resource(db, resource_id)
    response.headers["ETag"] = f'"{resource.lock_version}"'
    return resource


@router.patch(
    "/workspaces/{workspace_id}/resources/{resource_id}",
    response_model=ResourceRead,
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("resource.write")),
        Depends(require_csrf),
    ],
)
def patch_resource(
    workspace_id: UUID,
    resource_id: UUID,
    data: ResourceUpdate,
    request: Request,
    response: Response,
    if_match: str = Header(alias="If-Match"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ResourceRead:
    try:
        expected = int(if_match.strip('"'))
    except ValueError as exc:
        raise ApplicationError(
            code="validation.if_match",
            title="Invalid If-Match",
            status=422,
            detail="If-Match must contain the numeric lock version.",
        ) from exc
    before = get_resource(db, resource_id)
    updated = update_resource(
        db,
        resource_id=resource_id,
        expected_lock_version=expected,
        data=data,
    )
    record_change(
        db,
        workspace_id=workspace_id,
        actor_user_id=principal.user_id,
        action="resource.update",
        resource_type="resource",
        resource_id=resource_id,
        event_type="knowledge.resource_updated.v1",
        before={
            "title": before.title,
            "lifecycleStatus": before.lifecycle_status,
            "lockVersion": before.lock_version,
        },
        after={
            "title": updated.title,
            "lifecycleStatus": updated.lifecycle_status,
            "lockVersion": updated.lock_version,
        },
        request_id=request.state.request_id,
    )
    response.headers["ETag"] = f'"{updated.lock_version}"'
    return updated
