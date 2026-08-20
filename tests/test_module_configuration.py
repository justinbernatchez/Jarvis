from __future__ import annotations

import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from jarvis.db.session import (
    assume_application_role,
    set_actor_context,
    set_workspace_context,
)
from jarvis.governance.models import AuditEvent, OutboxEvent
from jarvis.platform.manifest import ModuleManifest, load_example_manifest
from jarvis.platform.models import (
    Module,
    ModuleDependency,
    ModuleDependencyResolution,
    ModuleInstallation,
    ModuleRelease,
    WorkspacePreferences,
)
from jarvis.platform.schemas import JarvisConfig
from jarvis.platform.service import apply_configuration_import, register_manifest
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from tests.conftest import DatabaseHarness, authenticate_client


def test_manifest_capability_validation_fails_closed() -> None:
    manifest = load_example_manifest()
    implementation_files = [
        "apps/web/src/FoundationExamplePage.tsx",
        "apps/web/src/LazyFoundationExamplePage.tsx",
        "apps/web/src/ExampleModuleRoute.tsx",
        "apps/web/src/moduleRegistry.tsx",
    ]
    implementation_hash = hashlib.sha256()
    for filename in implementation_files:
        implementation_hash.update(filename.encode())
        implementation_hash.update(b"\0")
        implementation_hash.update(Path(filename).read_bytes())
        implementation_hash.update(b"\0")
    assert manifest.code_digest == f"sha256:{implementation_hash.hexdigest()}"
    payload = manifest.model_dump(mode="json", by_alias=True)
    payload["routes"][0]["componentKey"] = "attacker.remote.component"
    with pytest.raises(ValidationError):
        ModuleManifest.model_validate(payload)

    unsafe_schema = manifest.model_dump(mode="json", by_alias=True)
    del unsafe_schema["configurationSchema"]["properties"]["welcomeMessage"]["x-jarvis-exportable"]
    with pytest.raises(ValidationError):
        ModuleManifest.model_validate(unsafe_schema)


def test_module_lifecycle_configuration_portability_and_audit(
    client,
    settings,
    database: DatabaseHarness,
    create_user_context,
) -> None:
    source = create_user_context("Module Source")
    target = create_user_context("Module Target")
    source_headers = authenticate_client(client, settings, source)

    catalog = client.get("/api/v1/modules")
    assert catalog.status_code == 200
    example = next(item for item in catalog.json() if item["moduleKey"] == "jarvis.example")
    assert "jarvis.example.page" in example["capabilities"]
    assert "jarvis.example.read" in example["capabilities"]

    install = client.post(
        f"/api/v1/workspaces/{source.workspace_id}/modules/jarvis.example",
        headers=source_headers,
        json={
            "semanticVersion": "0.1.0",
            "configuration": {"welcomeMessage": "Source workspace"},
        },
    )
    assert install.status_code == 201, install.text
    installation = install.json()
    assert installation["enabled"] is True

    resource = client.post(
        f"/api/v1/workspaces/{source.workspace_id}/resources",
        headers=source_headers,
        json={
            "typeKey": "foundation_record",
            "slug": "survives-module-removal",
            "title": "Historical user data",
            "payload": {},
        },
    )
    assert resource.status_code == 201
    resource_id = resource.json()["id"]

    navigation = client.get(f"/api/v1/workspaces/{source.workspace_id}/navigation")
    assert navigation.status_code == 200
    assert navigation.json()[0]["componentKey"] == "jarvis.example.page"

    disable = client.patch(
        f"/api/v1/workspaces/{source.workspace_id}/modules/jarvis.example",
        headers={**source_headers, "If-Match": f'"{installation["lockVersion"]}"'},
        json={"enabled": False},
    )
    assert disable.status_code == 200, disable.text
    assert disable.json()["enabled"] is False
    assert client.get(f"/api/v1/workspaces/{source.workspace_id}/navigation").json() == []

    enable = client.patch(
        f"/api/v1/workspaces/{source.workspace_id}/modules/jarvis.example",
        headers={**source_headers, "If-Match": f'"{disable.json()["lockVersion"]}"'},
        json={"enabled": True},
    )
    assert enable.status_code == 200

    preferences = {"density": "compact", "theme": "dark"}
    preference_response = client.put(
        f"/api/v1/workspaces/{source.workspace_id}/preferences",
        headers={**source_headers, "If-Match": '"1"'},
        json={"values": preferences},
    )
    assert preference_response.status_code == 200
    override_response = client.put(
        f"/api/v1/workspaces/{source.workspace_id}/navigation-overrides",
        headers=source_headers,
        json={
            "items": [
                {
                    "nodeKey": "jarvis.example.nav",
                    "label": "Foundation Proof",
                    "order": 7,
                    "hidden": False,
                }
            ]
        },
    )
    assert override_response.status_code == 204

    exported = client.get(f"/api/v1/workspaces/{source.workspace_id}/configuration/export")
    assert exported.status_code == 200
    assert "jarvis-config.json" in exported.headers["content-disposition"]
    configuration = exported.json()
    serialized = json.dumps(configuration).lower()
    assert "credential" not in serialized
    assert "secret" not in serialized
    assert configuration["modules"][0]["id"] == "jarvis.example"
    assert configuration["preferences"] == preferences
    assert configuration["navigationOverrides"][0]["nodeKey"] == "jarvis.example.nav"
    configuration["workflowDefaults"] = {"defaultView": "foundation"}
    configuration["personalCategories"] = ["platform"]

    target_headers = authenticate_client(client, settings, target)
    dry_run = client.post(
        f"/api/v1/workspaces/{target.workspace_id}/configuration/import/dry-run",
        headers=target_headers,
        json={"configuration": configuration},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["compatible"] is True
    assert dry_run.json()["actions"][0]["action"] == "install"
    assert dry_run.json()["actions"][0]["moduleKey"] == "jarvis.example"

    imported = client.post(
        f"/api/v1/workspaces/{target.workspace_id}/configuration/import",
        headers=target_headers,
        json={"configuration": configuration},
    )
    assert imported.status_code == 200, imported.text
    target_export = client.get(
        f"/api/v1/workspaces/{target.workspace_id}/configuration/export"
    ).json()
    assert target_export["modules"][0]["id"] == "jarvis.example"
    assert target_export["preferences"] == preferences
    assert target_export["navigationOverrides"][0]["label"] == "Foundation Proof"
    assert target_export["workflowDefaults"] == {"defaultView": "foundation"}
    assert target_export["personalCategories"] == ["platform"]

    repeated_dry_run = client.post(
        f"/api/v1/workspaces/{target.workspace_id}/configuration/import/dry-run",
        headers=target_headers,
        json={"configuration": configuration},
    )
    assert repeated_dry_run.status_code == 200
    assert repeated_dry_run.json()["changed"] is False
    assert repeated_dry_run.json()["actions"][0]["action"] == "noop"

    changed_configuration = copy.deepcopy(configuration)
    changed_configuration["modules"][0]["configuration"]["welcomeMessage"] = (
        "Updated portable configuration"
    )
    changed_dry_run = client.post(
        f"/api/v1/workspaces/{target.workspace_id}/configuration/import/dry-run",
        headers=target_headers,
        json={"configuration": changed_configuration},
    )
    assert changed_dry_run.status_code == 200
    assert changed_dry_run.json()["actions"][0]["action"] == "update"
    changed_import = client.post(
        f"/api/v1/workspaces/{target.workspace_id}/configuration/import",
        headers=target_headers,
        json={"configuration": changed_configuration},
    )
    assert changed_import.status_code == 200
    changed_export = client.get(
        f"/api/v1/workspaces/{target.workspace_id}/configuration/export"
    ).json()
    assert (
        changed_export["modules"][0]["configuration"]["welcomeMessage"]
        == "Updated portable configuration"
    )

    target_preferences = client.get(f"/api/v1/workspaces/{target.workspace_id}/preferences")
    secret_preference = client.put(
        f"/api/v1/workspaces/{target.workspace_id}/preferences",
        headers={
            **target_headers,
            "If-Match": target_preferences.headers["etag"],
        },
        json={"values": {"providerApiKey": "must-not-export"}},
    )
    assert secret_preference.status_code == 422
    assert secret_preference.json()["code"] == "validation.request"

    authenticate_client(client, settings, source)
    removed = client.delete(
        f"/api/v1/workspaces/{source.workspace_id}/modules/jarvis.example",
        headers={**source_headers, "If-Match": f'"{enable.json()["lockVersion"]}"'},
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "removed"
    assert client.get(f"/api/v1/workspaces/{source.workspace_id}/navigation").json() == []
    assert (
        client.get(f"/api/v1/workspaces/{source.workspace_id}/resources/{resource_id}").status_code
        == 200
    )

    with database.owner_factory() as session:
        installation_row = session.scalar(
            select(ModuleInstallation).where(ModuleInstallation.workspace_id == source.workspace_id)
        )
        assert installation_row is not None
        assert installation_row.status == "removed"
        audit_count = session.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workspace_id == source.workspace_id,
                AuditEvent.action == "module.install",
            )
        )
        outbox_count = session.scalar(
            select(func.count(OutboxEvent.id)).where(
                OutboxEvent.workspace_id == source.workspace_id,
                OutboxEvent.event_type == "platform.module_installed.v1",
            )
        )
        assert audit_count == 1
        assert outbox_count == 1
        install_event = session.scalar(
            select(OutboxEvent).where(
                OutboxEvent.workspace_id == source.workspace_id,
                OutboxEvent.event_type == "platform.module_installed.v1",
            )
        )
        assert install_event is not None
        assert "configuration" not in install_event.payload
        assert install_event.payload["configurationHash"]


def test_configuration_import_serializes_concurrent_full_state_updates(
    database: DatabaseHarness,
    create_user_context,
) -> None:
    context = create_user_context("Concurrent Configuration")
    barrier = Barrier(2)

    def apply_variant(message: str, density: str) -> None:
        configuration = JarvisConfig.model_validate(
            {
                "schemaVersion": "1.0",
                "exportedAt": "2026-08-19T12:00:00Z",
                "coreCompatibility": ">=0.1.0,<1.0.0",
                "modules": [
                    {
                        "id": "jarvis.example",
                        "version": "0.1.0",
                        "enabled": True,
                        "configuration": {"welcomeMessage": message},
                    }
                ],
                "navigationOverrides": [],
                "preferences": {"density": density, "theme": "dark"},
                "workflowDefaults": {},
                "personalCategories": [],
            }
        )
        with database.factory() as session, session.begin():
            assume_application_role(session)
            set_actor_context(session, context.user_id, context.session_id)
            set_workspace_context(session, context.workspace_id)
            barrier.wait()
            apply_configuration_import(
                session,
                workspace_id=context.workspace_id,
                actor_id=context.user_id,
                configuration=configuration,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(
            executor.map(
                lambda values: apply_variant(*values),
                [("Variant A", "compact"), ("Variant B", "comfortable")],
            )
        )

    with database.owner_factory() as session:
        installation = session.scalar(
            select(ModuleInstallation)
            .join(Module, Module.id == ModuleInstallation.module_id)
            .where(
                ModuleInstallation.workspace_id == context.workspace_id,
                Module.key == "jarvis.example",
            )
        )
        preferences = session.get(WorkspacePreferences, context.workspace_id)
        assert installation is not None
        assert preferences is not None
        final_state = (
            installation.configuration["welcomeMessage"],
            preferences.values["density"],
        )
        assert final_state in {
            ("Variant A", "compact"),
            ("Variant B", "comfortable"),
        }


def test_dependency_order_reverse_dependency_and_release_module_integrity(
    client,
    settings,
    database: DatabaseHarness,
    create_user_context,
) -> None:
    dependent_manifest = ModuleManifest.model_validate(
        {
            "manifestVersion": "1.0",
            "id": "aaa.dependent",
            "version": "0.1.0",
            "codeDigest": f"sha256:{'1' * 64}",
            "name": "Dependent",
            "description": "Dependency ordering proof.",
            "coreCompatibility": ">=0.1.0,<1.0.0",
            "dependencies": [{"moduleId": "jarvis.example", "version": ">=0.1.0,<1.0.0"}],
            "permissions": ["aaa.dependent.read"],
            "routes": [
                {
                    "key": "aaa.dependent.home",
                    "path": "/dependent",
                    "componentKey": "aaa.dependent.page",
                    "requiredPermission": "aaa.dependent.read",
                }
            ],
            "navigation": [
                {
                    "key": "aaa.dependent.nav",
                    "parentKey": None,
                    "routeKey": "aaa.dependent.home",
                    "label": "Dependent",
                    "iconKey": "blocks",
                    "defaultOrder": 200,
                }
            ],
            "components": [{"key": "aaa.dependent.page", "kind": "page"}],
            "flowHandlers": [],
            "dataProviders": [],
            "aiTools": [],
            "configurationSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        }
    )
    with database.owner_factory() as session, session.begin():
        register_manifest(session, dependent_manifest)

    context = create_user_context("Dependency User")
    headers = authenticate_client(client, settings, context)
    configuration = {
        "schemaVersion": "1.0",
        "exportedAt": "2026-08-19T12:00:00Z",
        "coreCompatibility": ">=0.1.0,<1.0.0",
        "modules": [
            {
                "id": "aaa.dependent",
                "version": "0.1.0",
                "enabled": True,
                "configuration": {},
            },
            {
                "id": "jarvis.example",
                "version": "0.1.0",
                "enabled": True,
                "configuration": {},
            },
        ],
        "navigationOverrides": [],
        "preferences": {},
        "workflowDefaults": {},
        "personalCategories": [],
    }
    dry_run = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/configuration/import/dry-run",
        headers=headers,
        json={"configuration": configuration},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert [item["moduleKey"] for item in dry_run.json()["actions"]] == [
        "jarvis.example",
        "aaa.dependent",
    ]
    disabled_dependency = copy.deepcopy(configuration)
    next(item for item in disabled_dependency["modules"] if item["id"] == "jarvis.example")[
        "enabled"
    ] = False
    invalid_dependency_plan = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/configuration/import/dry-run",
        headers=headers,
        json={"configuration": disabled_dependency},
    )
    assert invalid_dependency_plan.status_code == 200
    assert invalid_dependency_plan.json()["compatible"] is False
    applied = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/configuration/import",
        headers=headers,
        json={"configuration": configuration},
    )
    assert applied.status_code == 200, applied.text
    invalid_override = client.put(
        f"/api/v1/workspaces/{context.workspace_id}/navigation-overrides",
        headers=headers,
        json={"items": [{"nodeKey": "attacker.unknown.nav", "order": 1, "hidden": False}]},
    )
    assert invalid_override.status_code == 422
    override = client.put(
        f"/api/v1/workspaces/{context.workspace_id}/navigation-overrides",
        headers=headers,
        json={
            "items": [
                {"nodeKey": "jarvis.example.nav", "order": 300, "hidden": False},
                {"nodeKey": "aaa.dependent.nav", "order": 1, "hidden": False},
            ]
        },
    )
    assert override.status_code == 204
    navigation = client.get(f"/api/v1/workspaces/{context.workspace_id}/navigation").json()
    assert [item["key"] for item in navigation] == [
        "aaa.dependent.nav",
        "jarvis.example.nav",
    ]
    installations = client.get(f"/api/v1/workspaces/{context.workspace_id}/modules").json()
    example = next(item for item in installations if item["moduleKey"] == "jarvis.example")
    blocked = client.patch(
        f"/api/v1/workspaces/{context.workspace_id}/modules/jarvis.example",
        headers={**headers, "If-Match": f'"{example["lockVersion"]}"'},
        json={"enabled": False},
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "configuration.invalid"
    dependent = next(item for item in installations if item["moduleKey"] == "aaa.dependent")
    disabled_dependent = client.patch(
        f"/api/v1/workspaces/{context.workspace_id}/modules/aaa.dependent",
        headers={**headers, "If-Match": f'"{dependent["lockVersion"]}"'},
        json={"enabled": False},
    )
    assert disabled_dependent.status_code == 200
    disabled_target = client.patch(
        f"/api/v1/workspaces/{context.workspace_id}/modules/jarvis.example",
        headers={**headers, "If-Match": f'"{example["lockVersion"]}"'},
        json={"enabled": False},
    )
    assert disabled_target.status_code == 200
    invalid_reenable = client.patch(
        f"/api/v1/workspaces/{context.workspace_id}/modules/aaa.dependent",
        headers={
            **headers,
            "If-Match": f'"{disabled_dependent.json()["lockVersion"]}"',
        },
        json={"enabled": True},
    )
    assert invalid_reenable.status_code == 422
    reenabled_target = client.patch(
        f"/api/v1/workspaces/{context.workspace_id}/modules/jarvis.example",
        headers={
            **headers,
            "If-Match": f'"{disabled_target.json()["lockVersion"]}"',
        },
        json={"enabled": True},
    )
    assert reenabled_target.status_code == 200

    example_upgrade_payload = load_example_manifest().model_dump(
        mode="json",
        by_alias=True,
    )
    example_upgrade_payload["version"] = "0.2.0"
    example_upgrade_payload["codeDigest"] = f"sha256:{'4' * 64}"
    dependent_upgrade_payload = dependent_manifest.model_dump(
        mode="json",
        by_alias=True,
    )
    dependent_upgrade_payload["version"] = "0.2.0"
    dependent_upgrade_payload["codeDigest"] = f"sha256:{'5' * 64}"
    dependent_upgrade_payload["dependencies"][0]["version"] = ">=0.2.0,<1.0.0"
    with database.owner_factory() as session, session.begin():
        register_manifest(
            session,
            ModuleManifest.model_validate(example_upgrade_payload),
        )
        register_manifest(
            session,
            ModuleManifest.model_validate(dependent_upgrade_payload),
        )
    upgrade_configuration = copy.deepcopy(configuration)
    for module_config in upgrade_configuration["modules"]:
        module_config["version"] = "0.2.0"
    upgrade_plan = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/configuration/import/dry-run",
        headers=headers,
        json={"configuration": upgrade_configuration},
    )
    assert upgrade_plan.status_code == 200, upgrade_plan.text
    assert upgrade_plan.json()["compatible"] is True
    upgraded = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/configuration/import",
        headers=headers,
        json={"configuration": upgrade_configuration},
    )
    assert upgraded.status_code == 200, upgraded.text
    upgraded_installations = client.get(f"/api/v1/workspaces/{context.workspace_id}/modules").json()
    assert {item["semanticVersion"] for item in upgraded_installations} == {"0.2.0"}

    example_dependency_upgrade = load_example_manifest().model_dump(
        mode="json",
        by_alias=True,
    )
    example_dependency_upgrade["version"] = "0.3.0"
    example_dependency_upgrade["codeDigest"] = f"sha256:{'6' * 64}"
    with database.owner_factory() as session, session.begin():
        register_manifest(
            session,
            ModuleManifest.model_validate(example_dependency_upgrade),
        )
    dependency_only_configuration = copy.deepcopy(upgrade_configuration)
    next(
        item for item in dependency_only_configuration["modules"] if item["id"] == "jarvis.example"
    )["version"] = "0.3.0"
    dependency_only_plan = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/configuration/import/dry-run",
        headers=headers,
        json={"configuration": dependency_only_configuration},
    )
    assert dependency_only_plan.status_code == 200
    assert dependency_only_plan.json()["compatible"] is True
    assert (
        next(
            item
            for item in dependency_only_plan.json()["actions"]
            if item["moduleKey"] == "aaa.dependent"
        )["action"]
        == "noop"
    )
    dependency_only_apply = client.post(
        f"/api/v1/workspaces/{context.workspace_id}/configuration/import",
        headers=headers,
        json={"configuration": dependency_only_configuration},
    )
    assert dependency_only_apply.status_code == 200, dependency_only_apply.text
    with database.owner_factory() as session:
        resolution = session.scalar(
            select(ModuleDependencyResolution)
            .join(
                ModuleInstallation,
                ModuleInstallation.id == ModuleDependencyResolution.installation_id,
            )
            .join(Module, Module.id == ModuleInstallation.module_id)
            .where(
                ModuleInstallation.workspace_id == context.workspace_id,
                Module.key == "aaa.dependent",
            )
        )
        assert resolution is not None
        assert resolution.resolved_version == "0.3.0"

    isolated = create_user_context("Constraint User")
    with pytest.raises(IntegrityError), database.owner_factory() as session, session.begin():
        example_module = session.scalar(select(Module).where(Module.key == "jarvis.example"))
        dependent_release = session.scalar(
            select(ModuleRelease)
            .join(Module, Module.id == ModuleRelease.module_id)
            .where(
                Module.key == "aaa.dependent",
                ModuleRelease.semantic_version == "0.2.0",
            )
        )
        assert example_module is not None
        assert dependent_release is not None
        session.add(
            ModuleInstallation(
                id=uuid4(),
                workspace_id=isolated.workspace_id,
                module_id=example_module.id,
                module_release_id=dependent_release.id,
                enabled=True,
                status="installed",
                configuration={},
                lock_version=1,
                installed_by_user_id=isolated.user_id,
            )
        )
        session.flush()

    with database.owner_factory() as session, session.begin():
        example_module = session.scalar(select(Module).where(Module.key == "jarvis.example"))
        example_release = session.scalar(
            select(ModuleRelease)
            .join(Module, Module.id == ModuleRelease.module_id)
            .where(
                Module.key == "jarvis.example",
                ModuleRelease.semantic_version == "0.2.0",
            )
        )
        dependent_release = session.scalar(
            select(ModuleRelease)
            .join(Module, Module.id == ModuleRelease.module_id)
            .where(
                Module.key == "aaa.dependent",
                ModuleRelease.semantic_version == "0.2.0",
            )
        )
        dependency = session.scalar(
            select(ModuleDependency).where(
                ModuleDependency.module_release_id == dependent_release.id
            )
        )
        example_installation = session.scalar(
            select(ModuleInstallation).where(
                ModuleInstallation.workspace_id == context.workspace_id,
                ModuleInstallation.module_id == example_module.id,
            )
        )
        dependent_installation = session.scalar(
            select(ModuleInstallation).where(
                ModuleInstallation.workspace_id == context.workspace_id,
                ModuleInstallation.module_release_id == dependent_release.id,
            )
        )
        assert example_module is not None
        assert example_release is not None
        assert dependent_release is not None
        assert dependency is not None
        assert example_installation is not None
        assert dependent_installation is not None
        bad_release = ModuleRelease(
            module_id=example_module.id,
            semantic_version="2.0.0",
            manifest_version="1.0",
            core_compatibility=">=0.1.0,<1.0.0",
            code_digest=f"sha256:{'2' * 64}",
            manifest_digest=f"sha256:{'3' * 64}",
            configuration_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            manifest={},
            published_at=datetime.now(UTC),
        )
        session.add(bad_release)
        session.flush()
        integrity_values = {
            "dependency": dependency,
            "example_release": example_release,
            "dependent_release": dependent_release,
            "example_installation": example_installation,
            "dependent_installation": dependent_installation,
            "bad_release": bad_release,
        }

    with pytest.raises(IntegrityError), database.owner_factory() as session, session.begin():
        session.add(
            ModuleDependencyResolution(
                installation_id=integrity_values["example_installation"].id,
                dependency_id=integrity_values["dependency"].id,
                resolved_release_id=integrity_values["example_release"].id,
                target_module_id=integrity_values["example_release"].module_id,
                dependent_release_id=integrity_values["dependent_release"].id,
                version_range=integrity_values["dependency"].version_range,
                resolved_version=integrity_values["example_release"].semantic_version,
            )
        )
        session.flush()

    with pytest.raises(IntegrityError), database.owner_factory() as session, session.begin():
        session.execute(
            delete(ModuleDependencyResolution).where(
                ModuleDependencyResolution.installation_id
                == integrity_values["dependent_installation"].id,
                ModuleDependencyResolution.dependency_id == integrity_values["dependency"].id,
            )
        )
        session.add(
            ModuleDependencyResolution(
                installation_id=integrity_values["dependent_installation"].id,
                dependency_id=integrity_values["dependency"].id,
                resolved_release_id=integrity_values["bad_release"].id,
                target_module_id=integrity_values["bad_release"].module_id,
                dependent_release_id=integrity_values["dependent_release"].id,
                version_range=integrity_values["dependency"].version_range,
                resolved_version=integrity_values["bad_release"].semantic_version,
            )
        )
        session.flush()
