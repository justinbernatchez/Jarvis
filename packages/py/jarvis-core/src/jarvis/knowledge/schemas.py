from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from jarvis.core.serialization import ApiModel, DecimalString, PageInfo


class ResourceCreate(ApiModel):
    type_key: str = Field(min_length=1, max_length=150)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=200)
    title: str = Field(min_length=1, max_length=300)
    payload: dict[str, object] = Field(default_factory=dict)
    confidence: DecimalString | None = None


class ResourceUpdate(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    lifecycle_status: str | None = Field(
        default=None,
        pattern=r"^(active|archived|deleted)$",
    )


class ResourceRead(ApiModel):
    id: UUID
    type_key: str
    namespace_key: str
    scope: str
    workspace_id: UUID | None
    slug: str
    title: str
    lifecycle_status: str
    lock_version: int
    current_revision_id: UUID | None
    revision_number: int | None
    confidence: DecimalString | None
    created_at: datetime
    updated_at: datetime


class ResourcePage(ApiModel):
    items: list[ResourceRead]
    page: PageInfo
