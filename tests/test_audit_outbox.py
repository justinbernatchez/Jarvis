from __future__ import annotations

from uuid import uuid4

import pytest
from jarvis.governance.models import AuditEvent, OutboxEvent
from jarvis.governance.service import record_change
from sqlalchemy import func, select

from tests.conftest import DatabaseHarness


def test_audit_and_outbox_share_the_domain_transaction(
    database: DatabaseHarness,
    create_user_context,
) -> None:
    context = create_user_context("Transactional User")
    aggregate_id = uuid4()

    with (
        pytest.raises(RuntimeError),
        database.owner_factory() as session,
        session.begin(),
    ):
        record_change(
            session,
            workspace_id=context.workspace_id,
            actor_user_id=context.user_id,
            action="proof.rollback",
            resource_type="foundation_proof",
            resource_id=aggregate_id,
            event_type="foundation.proof_rolled_back.v1",
            before=None,
            after={"state": "should-not-commit"},
        )
        raise RuntimeError("force transaction rollback")

    with database.owner_factory() as session:
        audit_count = session.scalar(
            select(func.count(AuditEvent.id)).where(AuditEvent.resource_id == aggregate_id)
        )
        outbox_count = session.scalar(
            select(func.count(OutboxEvent.id)).where(OutboxEvent.aggregate_id == aggregate_id)
        )
        assert audit_count == 0
        assert outbox_count == 0

    with database.owner_factory() as session, session.begin():
        audit, outbox = record_change(
            session,
            workspace_id=context.workspace_id,
            actor_user_id=context.user_id,
            action="proof.commit",
            resource_type="foundation_proof",
            resource_id=aggregate_id,
            event_type="foundation.proof_committed.v1",
            before=None,
            after={"state": "committed"},
        )
        session.flush()
        audit_id = audit.id
        outbox_id = outbox.id

    with database.owner_factory() as session:
        assert session.get(AuditEvent, audit_id) is not None
        assert session.get(OutboxEvent, outbox_id) is not None
