# ADR-0009: Start with PostgreSQL-Backed Durable Jobs

- Status: Accepted with implementation gate
- Date: 2026-08-18

## Context

PDF processing, provider imports, embeddings, analytics, and report generation
must not block API requests. They require retries and crash recovery, but the
initial workload does not justify operating a separate broker.

## Decision

Define a `JobQueue` port. Procrastinate is the initial PostgreSQL-backed
candidate when the first durable pipeline is implemented, subject to an
adapter, migration, rolling-upgrade, and stalled-job recovery spike.

Run jobs in a separate worker process. A canonical JARVIS `operation_run` is
authoritative; queue internals are not user-visible state. The creating
transaction writes the operation plus an outbox event. An idempotent dispatcher
enqueues it and advances `pending_dispatch` to `queued`. Recovery republishes
undispatched events.

Treat delivery as at-least-once:

- payloads contain scoped IDs, not large data or credentials;
- handlers use stable idempotency keys;
- retries are bounded with backoff;
- stalled jobs are detected through heartbeat/lease behavior;
- each claimed attempt receives a generation/fencing token, and a stale worker
  cannot commit after losing its lease;
- cancellation is cooperative and permissions are revalidated before
  sensitive work or side effects;
- failures and cancellation are visible to the user;
- large inputs and outputs remain in PostgreSQL/object storage.

Queue schema changes must remain under the controlled migration process.
The implementation spike must either wrap/vendor the adapter's required SQL
changes into the ordered Alembic release or document and test one coordinated
queue migration lane. It must also provide operated stalled-job recovery,
dead-letter ownership, retention, and rolling worker compatibility.

## Consequences

Benefits:

- no additional broker is required initially;
- enqueueing can participate in PostgreSQL transaction patterns;
- the worker remains independently scalable;
- the queue implementation is replaceable behind a narrow port.

Costs:

- job traffic shares PostgreSQL capacity with application traffic;
- queue tables and retention need monitoring;
- outbox dispatch introduces a visible `pending_dispatch` state and eventual
  handoff;
- adapter-owned migrations and periodic recovery tasks require integration;
- very high throughput or complex orchestration may outgrow the adapter.

Move to a dedicated broker or workflow system only when queue throughput,
resource isolation, or long-running orchestration demonstrates the need.
If the implementation spike fails its conformance gates, choose another
PostgreSQL-backed adapter or a dedicated broker through a superseding ADR.

