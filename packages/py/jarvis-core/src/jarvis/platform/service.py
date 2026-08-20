from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from jsonschema import Draft202012Validator
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from jarvis.core.errors import (
    ConfigurationError,
    ConflictError,
    NotFoundError,
    PreconditionFailedError,
)
from jarvis.governance.service import payload_hash, record_change
from jarvis.identity.service import register_permissions
from jarvis.platform.manifest import ModuleManifest
from jarvis.platform.models import (
    Capability,
    Module,
    ModuleDependency,
    ModuleDependencyResolution,
    ModuleInstallation,
    ModuleRelease,
    ModuleReleaseCapability,
    NavigationNode,
    NavigationOverride,
    WorkspacePreferences,
)
from jarvis.platform.schemas import (
    ConfigImportAction,
    ConfigImportPlan,
    JarvisConfig,
    ModuleConfigExport,
    ModuleInstallationRead,
    ModuleReleaseRead,
    NavigationNodeRead,
    NavigationOverrideConfig,
    WorkflowDefaults,
    WorkspacePreferencesRead,
    WorkspacePreferenceValues,
)

CORE_VERSION = Version("0.1.0")
SECRET_KEY_PATTERN = re.compile(
    r"(secret|credential|password|private[_-]?key|authorization|"
    r"api[_-]?key|access[_-]?token|refresh[_-]?token|bearer[_-]?token)",
    re.IGNORECASE,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _ensure_no_secret_material(value: object, *, path: str = "configuration") -> None:
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        for key, nested in mapping.items():
            key_text = str(key)
            if SECRET_KEY_PATTERN.search(key_text):
                raise ConfigurationError(
                    f"{path}.{key_text} is secret material; use a credential binding instead."
                )
            _ensure_no_secret_material(nested, path=f"{path}.{key_text}")
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        sequence = cast(Sequence[object], value)
        for index, nested in enumerate(sequence):
            _ensure_no_secret_material(nested, path=f"{path}[{index}]")


def _capability_declarations(manifest: ModuleManifest) -> list[tuple[str, str, str]]:
    values: list[tuple[str, str, str]] = []
    values.extend((key, "permission", manifest.version) for key in manifest.permissions)
    values.extend((item.key, "route", manifest.version) for item in manifest.routes)
    values.extend((item.key, "component", manifest.version) for item in manifest.components)
    values.extend((item.key, "handler", item.version) for item in manifest.flow_handlers)
    values.extend((item.key, "provider", item.version) for item in manifest.data_providers)
    values.extend((item.key, "ai_tool", item.version) for item in manifest.ai_tools)
    return values


def register_manifest(session: Session, manifest: ModuleManifest) -> ModuleRelease:
    if CORE_VERSION not in SpecifierSet(manifest.core_compatibility):
        raise ConfigurationError(f"Module {manifest.id} is incompatible with core {CORE_VERSION}.")
    module = session.scalar(select(Module).where(Module.key == manifest.id))
    if module is None:
        module = Module(
            key=manifest.id,
            name=manifest.name,
            description=manifest.description,
            lifecycle_status="active",
        )
        session.add(module)
        session.flush()
    else:
        module.name = manifest.name
        module.description = manifest.description

    release = session.scalar(
        select(ModuleRelease).where(
            ModuleRelease.module_id == module.id,
            ModuleRelease.semantic_version == manifest.version,
        )
    )
    manifest_digest = manifest.manifest_digest()
    if release is not None:
        if (
            release.code_digest != manifest.code_digest
            or release.manifest_digest != manifest_digest
        ):
            raise ConflictError(
                "A module release cannot be replaced with different content.",
                code="configuration.release_digest_mismatch",
            )
        return release

    release = ModuleRelease(
        module_id=module.id,
        semantic_version=manifest.version,
        manifest_version=manifest.manifest_version,
        core_compatibility=manifest.core_compatibility,
        code_digest=manifest.code_digest,
        manifest_digest=manifest_digest,
        configuration_schema=manifest.configuration_schema,
        manifest=manifest.model_dump(mode="json", by_alias=True),
        published_at=_now(),
    )
    session.add(release)
    session.flush()

    for key, kind, implementation_version in _capability_declarations(manifest):
        capability = session.scalar(select(Capability).where(Capability.key == key))
        if capability is None:
            capability = Capability(module_id=module.id, key=key, kind=kind)
            session.add(capability)
            session.flush()
        elif capability.module_id != module.id or capability.kind != kind:
            raise ConflictError(
                f"Capability key {key} is already owned by another module or kind.",
                code="configuration.capability_collision",
            )
        session.add(
            ModuleReleaseCapability(
                module_release_id=release.id,
                capability_id=capability.id,
                module_id=module.id,
                implementation_version=implementation_version,
            )
        )

    register_permissions(session, manifest.permissions)

    routes = {route.key: route for route in manifest.routes}
    for node in manifest.navigation:
        route = routes[node.route_key]
        session.add(
            NavigationNode(
                module_release_id=release.id,
                key=node.key,
                parent_key=node.parent_key,
                route_key=route.key,
                path=route.path,
                component_key=route.component_key,
                label=node.label,
                icon_key=node.icon_key,
                default_order=node.default_order,
                required_permission=route.required_permission,
            )
        )

    for dependency in manifest.dependencies:
        target = session.scalar(select(Module).where(Module.key == dependency.module_id))
        if target is None:
            raise ConfigurationError(f"Missing dependency module: {dependency.module_id}")
        session.add(
            ModuleDependency(
                module_release_id=release.id,
                target_module_id=target.id,
                version_range=dependency.version,
            )
        )
    return release


def list_module_releases(session: Session) -> list[ModuleReleaseRead]:
    rows = session.execute(
        select(ModuleRelease, Module).join(Module, Module.id == ModuleRelease.module_id)
    ).all()
    result: list[ModuleReleaseRead] = []
    for release, module in rows:
        capabilities = list(
            session.scalars(
                select(Capability.key)
                .join(
                    ModuleReleaseCapability,
                    ModuleReleaseCapability.capability_id == Capability.id,
                )
                .where(ModuleReleaseCapability.module_release_id == release.id)
                .order_by(Capability.key)
            )
        )
        result.append(
            ModuleReleaseRead(
                module_key=module.key,
                name=module.name,
                description=module.description,
                semantic_version=release.semantic_version,
                capabilities=capabilities,
            )
        )
    return result


def _release(
    session: Session,
    module_key: str,
    semantic_version: str,
) -> tuple[Module, ModuleRelease]:
    row = session.execute(
        select(Module, ModuleRelease)
        .join(ModuleRelease, ModuleRelease.module_id == Module.id)
        .where(
            Module.key == module_key,
            ModuleRelease.semantic_version == semantic_version,
        )
    ).one_or_none()
    if row is None:
        raise NotFoundError("Compatible module release not found.")
    return row[0], row[1]


def _validate_configuration(release: ModuleRelease, configuration: dict[str, object]) -> None:
    _ensure_no_secret_material(configuration)
    errors = sorted(
        Draft202012Validator(cast(Any, release.configuration_schema)).iter_errors(  # pyright: ignore[reportUnknownMemberType]
            cast(Any, configuration)
        ),
        key=lambda item: list(item.path),
    )
    if errors:
        details = "; ".join(error.message for error in errors)
        raise ConfigurationError(f"Module configuration failed validation: {details}")


def _installation_read(
    installation: ModuleInstallation,
    module: Module,
    release: ModuleRelease,
) -> ModuleInstallationRead:
    return ModuleInstallationRead(
        id=installation.id,
        workspace_id=installation.workspace_id,
        module_key=module.key,
        semantic_version=release.semantic_version,
        enabled=installation.enabled,
        status=installation.status,
        configuration=installation.configuration,
        lock_version=installation.lock_version,
        created_at=installation.created_at,
        updated_at=installation.updated_at,
    )


def _lock_workspace_configuration(session: Session, workspace_id: UUID) -> None:
    lock_row = session.scalar(
        select(WorkspacePreferences.workspace_id)
        .where(WorkspacePreferences.workspace_id == workspace_id)
        .with_for_update()
    )
    if lock_row is None:
        raise NotFoundError("Workspace configuration foundation is missing.")


def _require_no_active_dependents(
    session: Session,
    *,
    workspace_id: UUID,
    target_module_id: UUID,
    allowed_dependents: frozenset[str] = frozenset(),
) -> None:
    dependents = set(
        session.scalars(
            select(Module.key)
            .join(ModuleInstallation, ModuleInstallation.module_id == Module.id)
            .join(
                ModuleDependency,
                ModuleDependency.module_release_id == ModuleInstallation.module_release_id,
            )
            .where(
                ModuleInstallation.workspace_id == workspace_id,
                ModuleInstallation.status == "installed",
                ModuleInstallation.enabled.is_(True),
                ModuleDependency.target_module_id == target_module_id,
            )
            .with_for_update(of=ModuleInstallation)
        )
    )
    blocked_dependents = dependents - allowed_dependents
    if blocked_dependents:
        raise ConfigurationError(
            "Module cannot be disabled, removed, or replaced while "
            + ", ".join(sorted(blocked_dependents))
            + " depends on it."
        )


def _reconcile_workspace_dependencies(session: Session, workspace_id: UUID) -> None:
    installation_rows = session.execute(
        select(ModuleInstallation, ModuleRelease)
        .join(ModuleRelease, ModuleRelease.id == ModuleInstallation.module_release_id)
        .where(
            ModuleInstallation.workspace_id == workspace_id,
            ModuleInstallation.status == "installed",
            ModuleInstallation.enabled.is_(True),
        )
        .with_for_update(of=ModuleInstallation)
    ).all()
    targets = {
        installation.module_id: (installation, release)
        for installation, release in installation_rows
    }
    for installation, release in installation_rows:
        dependencies = list(
            session.scalars(
                select(ModuleDependency).where(ModuleDependency.module_release_id == release.id)
            )
        )
        for dependency in dependencies:
            target = targets.get(dependency.target_module_id)
            if target is None:
                raise ConfigurationError(
                    "An enabled module dependency is missing during reconciliation."
                )
            _, target_release = target
            if Version(target_release.semantic_version) not in SpecifierSet(
                dependency.version_range
            ):
                raise ConfigurationError(
                    "An enabled module dependency is incompatible during reconciliation."
                )
            resolution = session.get(
                ModuleDependencyResolution,
                {
                    "installation_id": installation.id,
                    "dependency_id": dependency.id,
                },
            )
            if resolution is None:
                resolution = ModuleDependencyResolution(
                    installation_id=installation.id,
                    dependency_id=dependency.id,
                    resolved_release_id=target_release.id,
                    target_module_id=dependency.target_module_id,
                    dependent_release_id=release.id,
                    version_range=dependency.version_range,
                    resolved_version=target_release.semantic_version,
                )
                session.add(resolution)
            else:
                resolution.resolved_release_id = target_release.id
                resolution.target_module_id = dependency.target_module_id
                resolution.dependent_release_id = release.id
                resolution.version_range = dependency.version_range
                resolution.resolved_version = target_release.semantic_version


def get_installation(
    session: Session,
    *,
    workspace_id: UUID,
    module_key: str,
) -> ModuleInstallationRead:
    row = session.execute(
        select(ModuleInstallation, Module, ModuleRelease)
        .join(Module, Module.id == ModuleInstallation.module_id)
        .join(ModuleRelease, ModuleRelease.id == ModuleInstallation.module_release_id)
        .where(
            ModuleInstallation.workspace_id == workspace_id,
            Module.key == module_key,
        )
    ).one_or_none()
    if row is None:
        raise NotFoundError("Module installation not found.")
    return _installation_read(row[0], row[1], row[2])


def list_installations(session: Session, *, workspace_id: UUID) -> list[ModuleInstallationRead]:
    rows = session.execute(
        select(ModuleInstallation, Module, ModuleRelease)
        .join(Module, Module.id == ModuleInstallation.module_id)
        .join(ModuleRelease, ModuleRelease.id == ModuleInstallation.module_release_id)
        .where(ModuleInstallation.workspace_id == workspace_id)
        .order_by(Module.key)
    ).all()
    return [_installation_read(row[0], row[1], row[2]) for row in rows]


def install_module(
    session: Session,
    *,
    workspace_id: UUID,
    actor_id: UUID,
    module_key: str,
    semantic_version: str,
    configuration: dict[str, object],
    coordinated_module_keys: frozenset[str] = frozenset(),
    request_id: str | None = None,
) -> ModuleInstallationRead:
    _lock_workspace_configuration(session, workspace_id)
    module, release = _release(session, module_key, semantic_version)
    _validate_configuration(release, configuration)

    installation = session.scalar(
        select(ModuleInstallation)
        .where(
            ModuleInstallation.workspace_id == workspace_id,
            ModuleInstallation.module_id == module.id,
        )
        .with_for_update()
    )
    before = None
    if (
        installation is not None
        and installation.module_release_id == release.id
        and installation.enabled
        and installation.status == "installed"
        and installation.configuration == configuration
    ):
        return _installation_read(installation, module, release)
    if (
        installation is not None
        and installation.status == "installed"
        and not coordinated_module_keys
    ):
        raise ConflictError(
            "An installed module must be changed through a validated configuration import.",
            code="conflict.module_already_installed",
        )
    if installation is None:
        installation = ModuleInstallation(
            workspace_id=workspace_id,
            module_id=module.id,
            module_release_id=release.id,
            enabled=True,
            status="installed",
            configuration=configuration,
            lock_version=1,
            installed_by_user_id=actor_id,
        )
        session.add(installation)
        session.flush()
    else:
        if (
            installation.status == "installed"
            and installation.enabled
            and installation.module_release_id != release.id
        ):
            _require_no_active_dependents(
                session,
                workspace_id=workspace_id,
                target_module_id=module.id,
                allowed_dependents=coordinated_module_keys,
            )
        before = {
            "moduleKey": module.key,
            "version": installation.module_release_id,
            "enabled": installation.enabled,
            "status": installation.status,
        }
        session.execute(
            delete(ModuleDependencyResolution).where(
                ModuleDependencyResolution.installation_id == installation.id
            )
        )
        installation.module_release_id = release.id
        installation.enabled = True
        installation.status = "installed"
        installation.configuration = configuration
        installation.removed_at = None
        installation.lock_version += 1

    dependencies = list(
        session.scalars(
            select(ModuleDependency).where(ModuleDependency.module_release_id == release.id)
        )
    )
    for dependency in dependencies:
        resolved = session.scalar(
            select(ModuleRelease)
            .join(
                ModuleInstallation,
                ModuleInstallation.module_release_id == ModuleRelease.id,
            )
            .where(
                ModuleInstallation.workspace_id == workspace_id,
                ModuleInstallation.module_id == dependency.target_module_id,
                ModuleInstallation.status == "installed",
                ModuleInstallation.enabled.is_(True),
            )
            .with_for_update(of=ModuleInstallation)
        )
        if resolved is None or Version(resolved.semantic_version) not in SpecifierSet(
            dependency.version_range
        ):
            raise ConfigurationError("A compatible installed module dependency is required.")
        session.add(
            ModuleDependencyResolution(
                installation_id=installation.id,
                dependency_id=dependency.id,
                resolved_release_id=resolved.id,
                target_module_id=dependency.target_module_id,
                dependent_release_id=release.id,
                version_range=dependency.version_range,
                resolved_version=resolved.semantic_version,
            )
        )

    after = {
        "moduleKey": module.key,
        "semanticVersion": release.semantic_version,
        "enabled": installation.enabled,
        "status": installation.status,
        "configurationHash": payload_hash(installation.configuration),
    }
    record_change(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_id,
        action="module.install",
        resource_type="module_installation",
        resource_id=installation.id,
        event_type="platform.module_installed.v1",
        before=before,
        after=after,
        request_id=request_id,
    )
    session.flush()
    return _installation_read(installation, module, release)


def set_module_enabled(
    session: Session,
    *,
    workspace_id: UUID,
    actor_id: UUID,
    module_key: str,
    enabled: bool,
    expected_lock_version: int,
    request_id: str | None = None,
) -> ModuleInstallationRead:
    _lock_workspace_configuration(session, workspace_id)
    module, installation, release = _installation_row(
        session, workspace_id, module_key, for_update=True
    )
    if installation.lock_version != expected_lock_version:
        raise PreconditionFailedError("The module installation changed since it was read.")
    if installation.status != "installed":
        raise ConfigurationError("A removed module must be installed before it can be enabled.")
    if installation.enabled == enabled:
        return _installation_read(installation, module, release)
    if not enabled:
        _require_no_active_dependents(
            session,
            workspace_id=workspace_id,
            target_module_id=module.id,
        )
    before = {"enabled": installation.enabled, "status": installation.status}
    updated_id = session.scalar(
        update(ModuleInstallation)
        .where(
            ModuleInstallation.id == installation.id,
            ModuleInstallation.lock_version == expected_lock_version,
            ModuleInstallation.status == "installed",
        )
        .values(
            enabled=enabled,
            lock_version=ModuleInstallation.lock_version + 1,
            updated_at=func.now(),
        )
        .returning(ModuleInstallation.id)
    )
    if updated_id is None:
        raise PreconditionFailedError("The module installation changed since it was read.")
    if enabled:
        _reconcile_workspace_dependencies(session, workspace_id)
    else:
        session.execute(
            delete(ModuleDependencyResolution).where(
                ModuleDependencyResolution.installation_id == installation.id
            )
        )
    after = {"enabled": enabled, "status": installation.status}
    record_change(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_id,
        action="module.enable" if enabled else "module.disable",
        resource_type="module_installation",
        resource_id=installation.id,
        event_type="platform.module_enabled_changed.v1",
        before=before,
        after=after,
        request_id=request_id,
    )
    session.flush()
    session.expire_all()
    refreshed_module, refreshed_installation, refreshed_release = _installation_row(
        session, workspace_id, module_key
    )
    return _installation_read(refreshed_installation, refreshed_module, refreshed_release)


def remove_module(
    session: Session,
    *,
    workspace_id: UUID,
    actor_id: UUID,
    module_key: str,
    expected_lock_version: int,
    request_id: str | None = None,
) -> ModuleInstallationRead:
    _lock_workspace_configuration(session, workspace_id)
    module, installation, release = _installation_row(
        session, workspace_id, module_key, for_update=True
    )
    if installation.lock_version != expected_lock_version:
        raise PreconditionFailedError("The module installation changed since it was read.")
    if installation.status != "installed":
        return _installation_read(installation, module, release)
    _require_no_active_dependents(
        session,
        workspace_id=workspace_id,
        target_module_id=module.id,
    )
    before = {"enabled": installation.enabled, "status": installation.status}
    updated_id = session.scalar(
        update(ModuleInstallation)
        .where(
            ModuleInstallation.id == installation.id,
            ModuleInstallation.lock_version == expected_lock_version,
            ModuleInstallation.status == "installed",
        )
        .values(
            enabled=False,
            status="removed",
            removed_at=_now(),
            lock_version=ModuleInstallation.lock_version + 1,
            updated_at=func.now(),
        )
        .returning(ModuleInstallation.id)
    )
    if updated_id is None:
        raise PreconditionFailedError("The module installation changed since it was read.")
    after = {"enabled": False, "status": "removed"}
    record_change(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_id,
        action="module.remove",
        resource_type="module_installation",
        resource_id=installation.id,
        event_type="platform.module_removed.v1",
        before=before,
        after=after,
        request_id=request_id,
    )
    session.flush()
    session.expire_all()
    refreshed_module, refreshed_installation, refreshed_release = _installation_row(
        session, workspace_id, module_key
    )
    return _installation_read(refreshed_installation, refreshed_module, refreshed_release)


def _installation_row(
    session: Session,
    workspace_id: UUID,
    module_key: str,
    *,
    for_update: bool = False,
) -> tuple[Module, ModuleInstallation, ModuleRelease]:
    statement = (
        select(Module, ModuleInstallation, ModuleRelease)
        .join(ModuleInstallation, ModuleInstallation.module_id == Module.id)
        .join(ModuleRelease, ModuleRelease.id == ModuleInstallation.module_release_id)
        .where(
            ModuleInstallation.workspace_id == workspace_id,
            Module.key == module_key,
        )
    )
    if for_update:
        statement = statement.with_for_update(of=ModuleInstallation)
    row = session.execute(statement).one_or_none()
    if row is None:
        raise NotFoundError("Module installation not found.")
    return row[0], row[1], row[2]


def get_navigation(session: Session, *, workspace_id: UUID) -> list[NavigationNodeRead]:
    rows = session.execute(
        select(NavigationNode, NavigationOverride)
        .join(
            ModuleInstallation,
            ModuleInstallation.module_release_id == NavigationNode.module_release_id,
        )
        .outerjoin(
            NavigationOverride,
            (NavigationOverride.workspace_id == workspace_id)
            & (NavigationOverride.node_key == NavigationNode.key),
        )
        .where(
            ModuleInstallation.workspace_id == workspace_id,
            ModuleInstallation.status == "installed",
            ModuleInstallation.enabled.is_(True),
        )
        .order_by(NavigationNode.default_order, NavigationNode.key)
    ).all()
    navigation = [
        NavigationNodeRead(
            key=node.key,
            parent_key=node.parent_key,
            route_key=node.route_key,
            path=node.path,
            component_key=node.component_key,
            label=override.label if override and override.label else node.label,
            icon_key=node.icon_key,
            order=override.order if override and override.order is not None else node.default_order,
            hidden=override.hidden if override else False,
            required_permission=node.required_permission,
        )
        for node, override in rows
    ]
    return sorted(navigation, key=lambda item: (item.order, item.key))


def set_preferences(
    session: Session,
    *,
    workspace_id: UUID,
    values: WorkspacePreferenceValues,
    expected_lock_version: int,
) -> WorkspacePreferencesRead:
    _lock_workspace_configuration(session, workspace_id)
    serialized_values = values.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    preferences = session.scalar(
        select(WorkspacePreferences)
        .where(WorkspacePreferences.workspace_id == workspace_id)
        .with_for_update()
    )
    if preferences is None:
        raise NotFoundError("Workspace preferences not found.")
    if preferences.lock_version != expected_lock_version:
        raise PreconditionFailedError("Workspace preferences changed since they were read.")
    if preferences.values != serialized_values:
        updated = session.scalar(
            update(WorkspacePreferences)
            .where(
                WorkspacePreferences.workspace_id == workspace_id,
                WorkspacePreferences.lock_version == expected_lock_version,
            )
            .values(
                values=serialized_values,
                lock_version=WorkspacePreferences.lock_version + 1,
                updated_at=func.now(),
            )
            .returning(WorkspacePreferences.workspace_id)
        )
        if updated is None:
            raise PreconditionFailedError("Workspace preferences changed since they were read.")
        session.expire_all()
        preferences = session.get(WorkspacePreferences, workspace_id)
        if preferences is None:
            raise RuntimeError("Workspace preferences disappeared during update")
    session.flush()
    return WorkspacePreferencesRead(
        workspace_id=workspace_id,
        values=WorkspacePreferenceValues.model_validate(preferences.values),
        lock_version=preferences.lock_version,
    )


def get_preferences(
    session: Session,
    *,
    workspace_id: UUID,
) -> WorkspacePreferencesRead:
    preferences = session.get(WorkspacePreferences, workspace_id)
    if preferences is None:
        raise NotFoundError("Workspace preferences not found.")
    return WorkspacePreferencesRead(
        workspace_id=workspace_id,
        values=WorkspacePreferenceValues.model_validate(preferences.values),
        lock_version=preferences.lock_version,
    )


def replace_navigation_overrides(
    session: Session,
    *,
    workspace_id: UUID,
    overrides: list[NavigationOverrideConfig],
) -> bool:
    _lock_workspace_configuration(session, workspace_id)
    valid_keys = set(
        session.scalars(
            select(NavigationNode.key)
            .join(
                ModuleInstallation,
                ModuleInstallation.module_release_id == NavigationNode.module_release_id,
            )
            .where(
                ModuleInstallation.workspace_id == workspace_id,
                ModuleInstallation.status == "installed",
            )
        )
    )
    requested_keys = [item.node_key for item in overrides]
    if len(requested_keys) != len(set(requested_keys)):
        raise ConfigurationError("Navigation override keys must be unique.")
    unknown_keys = set(requested_keys) - valid_keys
    if unknown_keys:
        raise ConfigurationError(
            f"Navigation overrides reference unknown installed nodes: {sorted(unknown_keys)}"
        )
    existing = list(
        session.scalars(
            select(NavigationOverride)
            .where(NavigationOverride.workspace_id == workspace_id)
            .order_by(NavigationOverride.node_key)
        )
    )
    existing_values = [
        NavigationOverrideConfig(
            node_key=item.node_key,
            label=item.label,
            order=item.order,
            hidden=item.hidden,
        )
        for item in existing
    ]
    requested_values = sorted(overrides, key=lambda item: item.node_key)
    if existing_values == requested_values:
        return False
    session.execute(
        delete(NavigationOverride).where(NavigationOverride.workspace_id == workspace_id)
    )
    for override in overrides:
        session.add(
            NavigationOverride(
                workspace_id=workspace_id,
                node_key=override.node_key,
                label=override.label,
                order=override.order,
                hidden=override.hidden,
            )
        )
    session.flush()
    return True


def export_configuration(session: Session, *, workspace_id: UUID) -> JarvisConfig:
    installations = [
        item
        for item in list_installations(session, workspace_id=workspace_id)
        if item.status == "installed"
    ]
    preferences = session.get(WorkspacePreferences, workspace_id)
    for installation in installations:
        _ensure_no_secret_material(
            installation.configuration,
            path=f"modules.{installation.module_key}.configuration",
        )
    if preferences:
        _ensure_no_secret_material(preferences.values, path="preferences")
        _ensure_no_secret_material(
            preferences.workflow_defaults,
            path="workflowDefaults",
        )
    overrides = list(
        session.scalars(
            select(NavigationOverride)
            .where(NavigationOverride.workspace_id == workspace_id)
            .order_by(NavigationOverride.node_key)
        )
    )
    return JarvisConfig(
        exported_at=_now(),
        modules=[
            ModuleConfigExport(
                id=item.module_key,
                version=item.semantic_version,
                enabled=item.enabled,
                configuration=item.configuration,
            )
            for item in installations
        ],
        navigation_overrides=[
            NavigationOverrideConfig(
                node_key=item.node_key,
                label=item.label,
                order=item.order,
                hidden=item.hidden,
            )
            for item in overrides
        ],
        preferences=WorkspacePreferenceValues.model_validate(
            preferences.values if preferences else {}
        ),
        workflow_defaults=WorkflowDefaults.model_validate(
            preferences.workflow_defaults if preferences else {}
        ),
        personal_categories=preferences.personal_categories if preferences else [],
    )


def _topological_module_order(graph: dict[str, set[str]]) -> list[str]:
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module_key: str) -> None:
        if module_key in visited:
            return
        if module_key in visiting:
            raise ConfigurationError("Module dependency graph contains a cycle.")
        visiting.add(module_key)
        for dependency_key in sorted(graph.get(module_key, set())):
            visit(dependency_key)
        visiting.remove(module_key)
        visited.add(module_key)
        ordered.append(module_key)

    for key in sorted(graph):
        visit(key)
    return ordered


def dry_run_configuration_import(
    session: Session,
    *,
    workspace_id: UUID,
    configuration: JarvisConfig,
) -> ConfigImportPlan:
    compatible = CORE_VERSION in SpecifierSet(configuration.core_compatibility)
    warnings = ["Credentials and sessions are intentionally excluded from configuration imports."]
    preference_values = configuration.preferences.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    workflow_defaults = configuration.workflow_defaults.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    requested_by_key = {item.id: item for item in configuration.modules}
    if len(requested_by_key) != len(configuration.modules):
        raise ConfigurationError("Configuration contains duplicate module keys.")
    current = {
        item.module_key: item for item in list_installations(session, workspace_id=workspace_id)
    }
    resolved_by_key: dict[str, ModuleRelease] = {}
    errors_by_key: dict[str, str] = {}
    for requested in configuration.modules:
        resolved = _resolve_compatible_release(session, requested.id, requested.version)
        if resolved is None:
            compatible = False
            errors_by_key[requested.id] = "No compatible trusted release is registered."
            continue
        try:
            _validate_configuration(resolved, requested.configuration)
        except ConfigurationError as exc:
            compatible = False
            errors_by_key[requested.id] = exc.detail
            continue
        resolved_by_key[requested.id] = resolved

    dependency_graph: dict[str, set[str]] = {key: set() for key in resolved_by_key}
    for module_key, release in resolved_by_key.items():
        dependencies = session.execute(
            select(ModuleDependency, Module)
            .join(Module, Module.id == ModuleDependency.target_module_id)
            .where(ModuleDependency.module_release_id == release.id)
        ).all()
        for dependency, target_module in dependencies:
            requested_target = resolved_by_key.get(target_module.key)
            if requested_target is not None:
                target_request = requested_by_key[target_module.key]
                if not target_request.enabled:
                    compatible = False
                    errors_by_key[module_key] = (
                        f"Requested dependency {target_module.key} must be enabled."
                    )
                elif Version(requested_target.semantic_version) not in SpecifierSet(
                    dependency.version_range
                ):
                    compatible = False
                    errors_by_key[module_key] = (
                        f"Requested dependency {target_module.key} is incompatible."
                    )
                dependency_graph[module_key].add(target_module.key)
                continue
            installed_target = current.get(target_module.key)
            if (
                installed_target is None
                or installed_target.status != "installed"
                or not installed_target.enabled
                or Version(installed_target.semantic_version)
                not in SpecifierSet(dependency.version_range)
            ):
                compatible = False
                errors_by_key[module_key] = (
                    f"Compatible dependency {target_module.key} is not installed or imported."
                )

    try:
        ordered_keys = _topological_module_order(dependency_graph)
    except ConfigurationError as exc:
        compatible = False
        warnings.append(exc.detail)
        ordered_keys = list(resolved_by_key)

    actions: list[ConfigImportAction] = []
    action_keys = [
        *ordered_keys,
        *(key for key in errors_by_key if key not in ordered_keys),
    ]
    for module_key in action_keys:
        requested = requested_by_key[module_key]
        resolved = resolved_by_key.get(module_key)
        existing = current.get(module_key)
        if resolved is None or module_key in errors_by_key:
            actions.append(
                ConfigImportAction(
                    action="install" if existing is None else "update",
                    module_key=module_key,
                    requested_version=requested.version,
                    resolved_version=resolved.semantic_version if resolved else None,
                    compatible=False,
                    detail=errors_by_key[module_key],
                )
            )
            continue
        if existing is None or existing.status == "removed":
            action = "install"
        elif (
            existing.semantic_version != resolved.semantic_version
            or existing.configuration != requested.configuration
        ):
            action = "update"
        elif existing.enabled != requested.enabled:
            action = "enable" if requested.enabled else "disable"
        else:
            action = "noop"
        actions.append(
            ConfigImportAction(
                action=action,
                module_key=requested.id,
                requested_version=requested.version,
                resolved_version=resolved.semantic_version,
                compatible=True,
                detail="Compatible trusted release resolved.",
            )
        )

    for index, action in enumerate(actions):
        existing = current.get(action.module_key)
        resolved = resolved_by_key.get(action.module_key)
        if (
            action.action != "update"
            or existing is None
            or resolved is None
            or existing.semantic_version == resolved.semantic_version
        ):
            continue
        module = session.scalar(select(Module).where(Module.key == action.module_key))
        if module is None:
            continue
        active_dependents = set(
            session.scalars(
                select(Module.key)
                .join(ModuleInstallation, ModuleInstallation.module_id == Module.id)
                .join(
                    ModuleDependency,
                    ModuleDependency.module_release_id == ModuleInstallation.module_release_id,
                )
                .where(
                    ModuleInstallation.workspace_id == workspace_id,
                    ModuleInstallation.status == "installed",
                    ModuleInstallation.enabled.is_(True),
                    ModuleDependency.target_module_id == module.id,
                )
            )
        )
        coordinated_dependents = {
            key for key, request in requested_by_key.items() if request.enabled
        }
        missing_dependents = active_dependents - coordinated_dependents
        if missing_dependents:
            compatible = False
            actions[index] = action.model_copy(
                update={
                    "compatible": False,
                    "detail": (
                        "Coordinated upgrade must include active dependents: "
                        + ", ".join(sorted(missing_dependents))
                    ),
                }
            )

    preferences = session.get(WorkspacePreferences, workspace_id)
    current_overrides = [
        NavigationOverrideConfig(
            node_key=item.node_key,
            label=item.label,
            order=item.order,
            hidden=item.hidden,
        )
        for item in session.scalars(
            select(NavigationOverride)
            .where(NavigationOverride.workspace_id == workspace_id)
            .order_by(NavigationOverride.node_key)
        )
    ]
    requested_overrides = sorted(
        configuration.navigation_overrides,
        key=lambda item: item.node_key,
    )
    candidate_release_ids = {
        *(
            session.scalars(
                select(ModuleInstallation.module_release_id).where(
                    ModuleInstallation.workspace_id == workspace_id,
                    ModuleInstallation.status == "installed",
                )
            )
        ),
        *(release.id for release in resolved_by_key.values()),
    }
    valid_navigation_keys = set(
        session.scalars(
            select(NavigationNode.key).where(
                NavigationNode.module_release_id.in_(candidate_release_ids)
            )
        )
    )
    requested_navigation_keys = [item.node_key for item in requested_overrides]
    if len(requested_navigation_keys) != len(set(requested_navigation_keys)):
        compatible = False
        warnings.append("Navigation override keys must be unique.")
    unknown_navigation_keys = set(requested_navigation_keys) - valid_navigation_keys
    if unknown_navigation_keys:
        compatible = False
        warnings.append(
            "Unknown navigation override keys: " + ", ".join(sorted(unknown_navigation_keys))
        )
    changed = any(action.action != "noop" for action in actions)
    changed = (
        changed
        or preferences is None
        or (
            preferences.values != preference_values
            or preferences.workflow_defaults != workflow_defaults
            or preferences.personal_categories != configuration.personal_categories
        )
    )
    changed = changed or current_overrides != requested_overrides
    return ConfigImportPlan(
        compatible=compatible,
        changed=changed,
        actions=actions,
        warnings=warnings,
    )


def apply_configuration_import(
    session: Session,
    *,
    workspace_id: UUID,
    actor_id: UUID,
    configuration: JarvisConfig,
) -> ConfigImportPlan:
    _lock_workspace_configuration(session, workspace_id)
    plan = dry_run_configuration_import(
        session,
        workspace_id=workspace_id,
        configuration=configuration,
    )
    if not plan.compatible:
        raise ConfigurationError("Configuration import has unresolved compatibility errors.")
    preference_values = configuration.preferences.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    workflow_defaults = configuration.workflow_defaults.model_dump(
        mode="json", by_alias=True, exclude_none=True
    )
    by_key = {item.id: item for item in configuration.modules}
    coordinated_module_keys = frozenset(item.id for item in configuration.modules if item.enabled)
    for action in plan.actions:
        requested = by_key[action.module_key]
        if action.action in {"install", "update"}:
            result = install_module(
                session,
                workspace_id=workspace_id,
                actor_id=actor_id,
                module_key=action.module_key,
                semantic_version=action.resolved_version or requested.version,
                configuration=requested.configuration,
                coordinated_module_keys=coordinated_module_keys,
            )
            if result.enabled != requested.enabled:
                set_module_enabled(
                    session,
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    module_key=action.module_key,
                    enabled=requested.enabled,
                    expected_lock_version=result.lock_version,
                )
        elif action.action in {"enable", "disable"}:
            existing = get_installation(
                session,
                workspace_id=workspace_id,
                module_key=action.module_key,
            )
            set_module_enabled(
                session,
                workspace_id=workspace_id,
                actor_id=actor_id,
                module_key=action.module_key,
                enabled=requested.enabled,
                expected_lock_version=existing.lock_version,
            )

    session.flush()
    _reconcile_workspace_dependencies(session, workspace_id)

    preferences = session.get(WorkspacePreferences, workspace_id)
    if preferences is None:
        preferences = WorkspacePreferences(
            workspace_id=workspace_id,
            values=preference_values,
            workflow_defaults=workflow_defaults,
            personal_categories=configuration.personal_categories,
            lock_version=1,
        )
        session.add(preferences)
    elif (
        preferences.values != preference_values
        or preferences.workflow_defaults != workflow_defaults
        or preferences.personal_categories != configuration.personal_categories
    ):
        preferences.values = preference_values
        preferences.workflow_defaults = workflow_defaults
        preferences.personal_categories = configuration.personal_categories
        preferences.lock_version += 1

    replace_navigation_overrides(
        session,
        workspace_id=workspace_id,
        overrides=configuration.navigation_overrides,
    )
    session.flush()
    return plan


def _resolve_compatible_release(
    session: Session,
    module_key: str,
    requested_version: str,
) -> ModuleRelease | None:
    releases = list(
        session.scalars(
            select(ModuleRelease)
            .join(Module, Module.id == ModuleRelease.module_id)
            .where(Module.key == module_key)
        )
    )
    requested = Version(requested_version)
    exact = next(
        (release for release in releases if Version(release.semantic_version) == requested),
        None,
    )
    if exact and CORE_VERSION in SpecifierSet(exact.core_compatibility):
        return exact
    same_major = [
        release
        for release in releases
        if Version(release.semantic_version).major == requested.major
        and CORE_VERSION in SpecifierSet(release.core_compatibility)
    ]
    if not same_major:
        return None
    return max(same_major, key=lambda release: Version(release.semantic_version))
