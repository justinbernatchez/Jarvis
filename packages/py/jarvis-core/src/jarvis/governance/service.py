from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from jarvis.governance.models import AuditEvent, OutboxEvent


def _now() -> datetime:
    return datetime.now(UTC)


def payload_hash(value: Mapping[str, object] | None) -> str | None:
    if value is None:
        return None
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def record_change(
    session: Session,
    *,
    workspace_id: UUID | None,
    actor_user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID,
    event_type: str,
    before: Mapping[str, object] | None,
    after: Mapping[str, object],
    request_id: str | None = None,
) -> tuple[AuditEvent, OutboxEvent]:
    now = _now()
    audit = AuditEvent(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        outcome="succeeded",
        before_hash=payload_hash(before),
        after_hash=payload_hash(after),
        event_metadata={"changedFields": sorted(after.keys())},
        created_at=now,
    )
    outbox = OutboxEvent(
        workspace_id=workspace_id,
        event_type=event_type,
        aggregate_type=resource_type,
        aggregate_id=resource_id,
        payload=dict(after),
        occurred_at=now,
        attempts=0,
    )
    session.add_all((audit, outbox))
    return audit, outbox
