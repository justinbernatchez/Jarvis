from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from jarvis.core.serialization import ApiModel


class UserRead(ApiModel):
    id: UUID
    display_name: str
    primary_email: str
    status: str


class WorkspaceCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    kind: str = Field(default="personal", pattern=r"^(personal|team)$")


class WorkspaceRead(ApiModel):
    id: UUID
    name: str
    slug: str
    kind: str
    status: str
    lock_version: int
    created_at: datetime
    updated_at: datetime


class MembershipRead(ApiModel):
    workspace_id: UUID
    user_id: UUID
    role_key: str
    status: str


class CurrentUserRead(ApiModel):
    user: UserRead
    memberships: list[MembershipRead]


class SessionRead(ApiModel):
    authenticated: bool
    user: UserRead
    csrf_token: str


class Principal(ApiModel):
    user_id: UUID
    session_id: UUID
    auth_time: datetime
