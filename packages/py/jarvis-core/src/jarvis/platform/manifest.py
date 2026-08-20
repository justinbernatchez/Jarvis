from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field, model_validator


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(item.capitalize() for item in rest)


def _validate_exportable_configuration_schema(
    schema: dict[str, object],
    *,
    path: str = "configuration",
) -> None:
    properties_value = schema.get("properties", {})
    if not isinstance(properties_value, dict):
        raise ValueError(f"{path}.properties must be an object")
    properties = cast(dict[str, object], properties_value)
    for property_name, property_value in properties.items():
        if not isinstance(property_value, dict):
            raise ValueError(f"{path}.{property_name} schema must be an object")
        property_schema = cast(dict[str, object], property_value)
        if property_schema.get("x-jarvis-exportable") is not True:
            raise ValueError(
                f"{path}.{property_name} must explicitly declare "
                "x-jarvis-exportable=true; credentials belong in secret bindings"
            )
        if property_schema.get("type") == "object":
            _validate_exportable_configuration_schema(
                property_schema,
                path=f"{path}.{property_name}",
            )


class ManifestModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda value: _to_camel(value),
        populate_by_name=True,
        extra="forbid",
    )


class ModuleDependencySpec(ManifestModel):
    module_id: str
    version: str = Field(
        pattern=r"^(?:>=|>|<=|<|==)\d+\.\d+\.\d+(?:,(?:>=|>|<=|<|==)\d+\.\d+\.\d+)*$"
    )


class RouteSpec(ManifestModel):
    key: str
    path: str
    component_key: str
    required_permission: str


class NavigationSpec(ManifestModel):
    key: str
    parent_key: str | None = None
    route_key: str
    label: str
    icon_key: str
    default_order: int


class ComponentSpec(ManifestModel):
    key: str
    kind: str = Field(pattern=r"^(page|panel|widget)$")


class VersionedCapabilitySpec(ManifestModel):
    key: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")


class ModuleManifest(ManifestModel):
    manifest_version: str
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]+$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    code_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    name: str
    description: str
    core_compatibility: str = Field(
        pattern=r"^(?:>=|>|<=|<|==)\d+\.\d+\.\d+(?:,(?:>=|>|<=|<|==)\d+\.\d+\.\d+)*$"
    )
    dependencies: list[ModuleDependencySpec] = []
    permissions: list[str] = []
    routes: list[RouteSpec] = []
    navigation: list[NavigationSpec] = []
    components: list[ComponentSpec] = []
    flow_handlers: list[VersionedCapabilitySpec] = []
    data_providers: list[VersionedCapabilitySpec] = []
    ai_tools: list[VersionedCapabilitySpec] = []
    configuration_schema: dict[str, object] = {}

    @model_validator(mode="after")
    def validate_trusted_references(self) -> ModuleManifest:
        try:
            if str(Version(self.version)) != self.version:
                raise ValueError("Module version must use normalized semantic form")
            SpecifierSet(self.core_compatibility)
            for dependency in self.dependencies:
                SpecifierSet(dependency.version)
        except (InvalidVersion, InvalidSpecifier) as exc:
            raise ValueError("Module versions and ranges must be valid") from exc

        prefix = f"{self.id}."
        component_keys = {item.key for item in self.components}
        route_keys = {item.key for item in self.routes}
        permission_keys = set(self.permissions)
        all_keys = [
            *permission_keys,
            *component_keys,
            *route_keys,
            *(item.key for item in self.navigation),
            *(item.key for item in self.flow_handlers),
            *(item.key for item in self.data_providers),
            *(item.key for item in self.ai_tools),
        ]
        if len(all_keys) != len(set(all_keys)):
            raise ValueError("Manifest capability keys must be unique")
        if any(not key.startswith(prefix) for key in all_keys):
            raise ValueError(f"All capability keys must start with {prefix}")
        for route in self.routes:
            if (
                not route.path.startswith("/")
                or route.path.startswith("//")
                or "\\" in route.path
                or any(ord(character) < 32 for character in route.path)
            ):
                raise ValueError(f"Route path is not a safe local path: {route.path}")
            if route.component_key not in component_keys:
                raise ValueError(f"Unknown component key: {route.component_key}")
            if route.required_permission not in permission_keys:
                raise ValueError(f"Unknown permission key: {route.required_permission}")
        navigation_keys = {item.key for item in self.navigation}
        if len(navigation_keys) != len(self.navigation):
            raise ValueError("Navigation keys must be unique")
        parent_by_key = {item.key: item.parent_key for item in self.navigation}
        for node in self.navigation:
            if node.route_key not in route_keys:
                raise ValueError(f"Unknown route key: {node.route_key}")
            if node.parent_key is not None and node.parent_key not in navigation_keys:
                raise ValueError(f"Unknown navigation parent: {node.parent_key}")
            seen: set[str] = set()
            current: str | None = node.key
            while current is not None:
                if current in seen:
                    raise ValueError("Navigation hierarchy contains a cycle")
                seen.add(current)
                current = parent_by_key.get(current)
        if self.configuration_schema.get("additionalProperties") is not False:
            raise ValueError("Module configuration schemas must fail closed")
        Draft202012Validator.check_schema(self.configuration_schema)
        _validate_exportable_configuration_schema(self.configuration_schema)
        return self

    def manifest_digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json", by_alias=True),
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def load_manifest(path: Path) -> ModuleManifest:
    return ModuleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def load_example_manifest() -> ModuleManifest:
    return load_manifest(Path(__file__).parent / "manifests" / "example-module.json")
