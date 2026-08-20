from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field

from jarvis.core.serialization import ApiModel

CategoryLabel = Annotated[
    str,
    Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9 _.-]+$"),
]


class ModuleReleaseRead(ApiModel):
    module_key: str
    name: str
    description: str
    semantic_version: str
    capabilities: list[str]


class ModuleInstallRequest(ApiModel):
    semantic_version: str
    configuration: dict[str, object] = Field(default_factory=dict)


class ModuleEnabledUpdate(ApiModel):
    enabled: bool


class ModuleInstallationRead(ApiModel):
    id: UUID
    workspace_id: UUID
    module_key: str
    semantic_version: str
    enabled: bool
    status: str
    configuration: dict[str, object]
    lock_version: int
    created_at: datetime
    updated_at: datetime


class NavigationNodeRead(ApiModel):
    key: str
    parent_key: str | None
    route_key: str
    path: str
    component_key: str
    label: str
    icon_key: str
    order: int
    hidden: bool
    required_permission: str


class WorkspacePreferenceValues(ApiModel):
    density: Literal["compact", "comfortable"] | None = None
    theme: Literal["dark", "light", "system"] | None = None


class WorkflowDefaults(ApiModel):
    default_view: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9._-]+$",
        max_length=100,
    )


class WorkspacePreferencesUpdate(ApiModel):
    values: WorkspacePreferenceValues


class WorkspacePreferencesRead(ApiModel):
    workspace_id: UUID
    values: WorkspacePreferenceValues
    lock_version: int


class NavigationOverrideConfig(ApiModel):
    node_key: str
    label: str | None = None
    order: int | None = None
    hidden: bool = False


class NavigationOverridesUpdate(ApiModel):
    items: list[NavigationOverrideConfig]


class ModuleConfigExport(ApiModel):
    id: str
    version: str
    enabled: bool
    configuration: dict[str, object]


class JarvisConfig(ApiModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    exported_at: datetime
    core_compatibility: str = ">=0.1.0,<1.0.0"
    modules: list[ModuleConfigExport]
    navigation_overrides: list[NavigationOverrideConfig]
    preferences: WorkspacePreferenceValues
    workflow_defaults: WorkflowDefaults = Field(default_factory=WorkflowDefaults)
    personal_categories: list[CategoryLabel] = Field(
        default_factory=list,
        max_length=100,
    )


class ConfigImportRequest(ApiModel):
    configuration: JarvisConfig


class ConfigImportAction(ApiModel):
    action: Literal["install", "update", "enable", "disable", "noop"]
    module_key: str
    requested_version: str
    resolved_version: str | None
    compatible: bool
    detail: str


class ConfigImportPlan(ApiModel):
    compatible: bool
    changed: bool
    actions: list[ConfigImportAction]
    warnings: list[str]
