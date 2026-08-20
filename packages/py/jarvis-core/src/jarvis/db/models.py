"""Import all initial-slice models for SQLAlchemy metadata registration."""

from jarvis.governance.models import AuditEvent, OutboxEvent
from jarvis.identity.models import (
    AuthIdentity,
    OIDCLoginTransaction,
    Permission,
    Role,
    RolePermission,
    User,
    UserSession,
    Workspace,
    WorkspaceMembership,
)
from jarvis.knowledge.models import (
    Resource,
    ResourceNamespace,
    ResourceRevision,
    ResourceRevisionLifecycleEvent,
    ResourceType,
)
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

__all__ = [
    "AuditEvent",
    "AuthIdentity",
    "Capability",
    "Module",
    "ModuleDependency",
    "ModuleDependencyResolution",
    "ModuleInstallation",
    "ModuleRelease",
    "ModuleReleaseCapability",
    "NavigationNode",
    "NavigationOverride",
    "OIDCLoginTransaction",
    "OutboxEvent",
    "Permission",
    "Resource",
    "ResourceNamespace",
    "ResourceRevision",
    "ResourceRevisionLifecycleEvent",
    "ResourceType",
    "Role",
    "RolePermission",
    "User",
    "UserSession",
    "Workspace",
    "WorkspaceMembership",
    "WorkspacePreferences",
]
