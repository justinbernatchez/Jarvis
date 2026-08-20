# ADR-0011: Use Embedded PostgreSQL for Local Foundation Tests

- Status: Accepted
- Date: 2026-08-19

## Context

The Phase 1 implementation host does not have Docker or a system PostgreSQL
installation. The mandatory migration and RLS gates require a real PostgreSQL
server; SQLite cannot validate schemas, roles, composite constraints, or row
security.

## Decision

Use `pgembed` as a development/test-only dependency to launch an isolated real
PostgreSQL server for local automated tests. The embedded wheel currently
provides PostgreSQL 17.9 on Windows.

Retain PostgreSQL 18.6 as the approved development/production target:

- Docker Compose uses PostgreSQL 18.6;
- CI must run the same migration/RLS suite against PostgreSQL 18.6;
- local embedded tests are a fast fallback, not the release-version gate;
- no application runtime depends on `pgembed`.

## Consequences

Benefits:

- mandatory database security tests run without administrator access or
  Docker;
- tests still exercise real PostgreSQL behavior;
- each suite can own an isolated temporary cluster.

Costs:

- local embedded PostgreSQL is one major version behind the approved target;
- PostgreSQL 18-specific behavior is verified only in containerized CI/dev;
- the wheel is a test supply-chain dependency and must be pinned/scanned.

Phase 1 cannot be declared production-ready solely from the embedded run. The
PostgreSQL 18.6 CI job is part of the release gate.

