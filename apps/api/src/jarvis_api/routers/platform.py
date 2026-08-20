from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status
from jarvis.core.errors import ApplicationError, AuthorizationError
from jarvis.governance.service import record_change
from jarvis.identity.schemas import Principal
from jarvis.identity.service import require_permission
from jarvis.platform.schemas import (
    ConfigImportPlan,
    ConfigImportRequest,
    JarvisConfig,
    ModuleEnabledUpdate,
    ModuleInstallationRead,
    ModuleInstallRequest,
    ModuleReleaseRead,
    NavigationNodeRead,
    NavigationOverridesUpdate,
    WorkspacePreferencesRead,
    WorkspacePreferencesUpdate,
)
from jarvis.platform.service import (
    apply_configuration_import,
    dry_run_configuration_import,
    export_configuration,
    get_navigation,
    get_preferences,
    install_module,
    list_installations,
    list_module_releases,
    remove_module,
    replace_navigation_overrides,
    set_module_enabled,
    set_preferences,
)
from sqlalchemy.orm import Session

from jarvis_api.dependencies import (
    get_db,
    get_principal,
    permission,
    require_csrf,
    workspace_scope,
)

router = APIRouter(tags=["platform"])
ETAG_HEADER = {
    "description": "Quoted optimistic lock version.",
    "schema": {"type": "string"},
}


@router.get("/modules", response_model=list[ModuleReleaseRead])
def module_catalog(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
) -> list[ModuleReleaseRead]:
    return list_module_releases(db)


@router.get(
    "/workspaces/{workspace_id}/modules",
    response_model=list[ModuleInstallationRead],
    dependencies=[Depends(workspace_scope), Depends(permission("module.read"))],
)
def workspace_modules(
    workspace_id: UUID,
    db: Session = Depends(get_db),
) -> list[ModuleInstallationRead]:
    return list_installations(db, workspace_id=workspace_id)


@router.post(
    "/workspaces/{workspace_id}/modules/{module_key}",
    response_model=ModuleInstallationRead,
    status_code=status.HTTP_201_CREATED,
    responses={201: {"headers": {"ETag": ETAG_HEADER}}},
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("module.manage")),
        Depends(require_csrf),
    ],
)
def install_workspace_module(
    workspace_id: UUID,
    module_key: str,
    data: ModuleInstallRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ModuleInstallationRead:
    result = install_module(
        db,
        workspace_id=workspace_id,
        actor_id=principal.user_id,
        module_key=module_key,
        semantic_version=data.semantic_version,
        configuration=data.configuration,
        request_id=request.state.request_id,
    )
    response.headers["ETag"] = f'"{result.lock_version}"'
    return result


@router.patch(
    "/workspaces/{workspace_id}/modules/{module_key}",
    response_model=ModuleInstallationRead,
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("module.manage")),
        Depends(require_csrf),
    ],
)
def update_workspace_module(
    workspace_id: UUID,
    module_key: str,
    data: ModuleEnabledUpdate,
    request: Request,
    response: Response,
    if_match: str = Header(alias="If-Match"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ModuleInstallationRead:
    expected = _if_match(if_match)
    result = set_module_enabled(
        db,
        workspace_id=workspace_id,
        actor_id=principal.user_id,
        module_key=module_key,
        enabled=data.enabled,
        expected_lock_version=expected,
        request_id=request.state.request_id,
    )
    response.headers["ETag"] = f'"{result.lock_version}"'
    return result


@router.delete(
    "/workspaces/{workspace_id}/modules/{module_key}",
    response_model=ModuleInstallationRead,
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("module.manage")),
        Depends(require_csrf),
    ],
)
def remove_workspace_module(
    workspace_id: UUID,
    module_key: str,
    request: Request,
    response: Response,
    if_match: str = Header(alias="If-Match"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ModuleInstallationRead:
    result = remove_module(
        db,
        workspace_id=workspace_id,
        actor_id=principal.user_id,
        module_key=module_key,
        expected_lock_version=_if_match(if_match),
        request_id=request.state.request_id,
    )
    response.headers["ETag"] = f'"{result.lock_version}"'
    return result


@router.get(
    "/workspaces/{workspace_id}/navigation",
    response_model=list[NavigationNodeRead],
    dependencies=[Depends(workspace_scope)],
)
def navigation(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> list[NavigationNodeRead]:
    visible: list[NavigationNodeRead] = []
    for node in get_navigation(db, workspace_id=workspace_id):
        try:
            require_permission(
                db,
                user_id=principal.user_id,
                workspace_id=workspace_id,
                permission_key=node.required_permission,
            )
        except AuthorizationError:
            continue
        visible.append(node)
    return visible


@router.get(
    "/workspaces/{workspace_id}/preferences",
    response_model=WorkspacePreferencesRead,
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("configuration.read")),
    ],
)
def read_preferences(
    workspace_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> WorkspacePreferencesRead:
    result = get_preferences(db, workspace_id=workspace_id)
    response.headers["ETag"] = f'"{result.lock_version}"'
    return result


@router.put(
    "/workspaces/{workspace_id}/preferences",
    response_model=WorkspacePreferencesRead,
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("configuration.write")),
        Depends(require_csrf),
    ],
)
def update_preferences(
    workspace_id: UUID,
    data: WorkspacePreferencesUpdate,
    request: Request,
    response: Response,
    if_match: str = Header(alias="If-Match"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> WorkspacePreferencesRead:
    result = set_preferences(
        db,
        workspace_id=workspace_id,
        values=data.values,
        expected_lock_version=_if_match(if_match),
    )
    preference_values = data.values.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    record_change(
        db,
        workspace_id=workspace_id,
        actor_user_id=principal.user_id,
        action="configuration.preferences.update",
        resource_type="workspace_configuration",
        resource_id=workspace_id,
        event_type="platform.preferences_updated.v1",
        before=None,
        after={"preferences": preference_values},
        request_id=request.state.request_id,
    )
    response.headers["ETag"] = f'"{result.lock_version}"'
    return result


@router.put(
    "/workspaces/{workspace_id}/navigation-overrides",
    status_code=204,
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("configuration.write")),
        Depends(require_csrf),
    ],
)
def update_navigation_overrides(
    workspace_id: UUID,
    data: NavigationOverridesUpdate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> Response:
    replace_navigation_overrides(db, workspace_id=workspace_id, overrides=data.items)
    record_change(
        db,
        workspace_id=workspace_id,
        actor_user_id=principal.user_id,
        action="configuration.navigation.update",
        resource_type="workspace_configuration",
        resource_id=workspace_id,
        event_type="platform.navigation_overrides_updated.v1",
        before=None,
        after={"nodeKeys": [item.node_key for item in data.items]},
        request_id=request.state.request_id,
    )
    return Response(status_code=204)


@router.get(
    "/workspaces/{workspace_id}/configuration/export",
    response_model=JarvisConfig,
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("configuration.read")),
    ],
)
def export_workspace_configuration(
    workspace_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> JarvisConfig:
    response.headers["Content-Disposition"] = 'attachment; filename="jarvis-config.json"'
    return export_configuration(db, workspace_id=workspace_id)


@router.post(
    "/workspaces/{workspace_id}/configuration/import/dry-run",
    response_model=ConfigImportPlan,
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("configuration.write")),
        Depends(require_csrf),
    ],
)
def dry_run_workspace_configuration_import(
    workspace_id: UUID,
    data: ConfigImportRequest,
    db: Session = Depends(get_db),
) -> ConfigImportPlan:
    return dry_run_configuration_import(
        db,
        workspace_id=workspace_id,
        configuration=data.configuration,
    )


@router.post(
    "/workspaces/{workspace_id}/configuration/import",
    response_model=ConfigImportPlan,
    dependencies=[
        Depends(workspace_scope),
        Depends(permission("configuration.write")),
        Depends(require_csrf),
    ],
)
def import_workspace_configuration(
    workspace_id: UUID,
    data: ConfigImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> ConfigImportPlan:
    plan = apply_configuration_import(
        db,
        workspace_id=workspace_id,
        actor_id=principal.user_id,
        configuration=data.configuration,
    )
    if plan.changed:
        record_change(
            db,
            workspace_id=workspace_id,
            actor_user_id=principal.user_id,
            action="configuration.import",
            resource_type="workspace_configuration",
            resource_id=workspace_id,
            event_type="platform.configuration_imported.v1",
            before=None,
            after={"moduleKeys": [item.module_key for item in plan.actions]},
            request_id=request.state.request_id,
        )
    return plan


def _if_match(value: str | None) -> int:
    if value is None:
        raise ApplicationError(
            code="validation.precondition_required",
            title="Precondition required",
            status=428,
            detail="If-Match is required for this update.",
        )
    try:
        return int(value.strip('"'))
    except ValueError as exc:
        raise ApplicationError(
            code="validation.if_match",
            title="Invalid If-Match",
            status=422,
            detail="If-Match must contain the numeric lock version.",
        ) from exc
