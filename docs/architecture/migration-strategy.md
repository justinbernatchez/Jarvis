# JARVIS Migration and Content Strategy

- Status: Phase 0 baseline
- Date: 2026-08-18

## 1. Principles

- Every schema change is represented by an Alembic migration.
- Production databases are never changed manually.
- One PostgreSQL database uses one ordered migration history.
- Bounded contexts own tables, but not independent migration heads.
- Schema migrations, data backfills, and product content releases are
  different artifacts.
- Production recovery favors forward fixes and restored backups over unsafe
  automatic downgrade.
- Migrations are compatible with rolling API/worker deployment.

## 2. Repository layout

```text
database/
  migrations/
    env.py
    script.py.mako
    versions/
  seeds/
    development/
    demo/
  content/
    packages/
  snapshots/
```

Migration filenames use:

```text
YYYYMMDD_HHMM_<context>_<purpose>.py
```

Each revision includes:

- context owner;
- purpose and compatibility notes;
- expected lock/scan risk;
- upgrade steps;
- downgrade only when safe and truthful;
- follow-up/backfill reference when applicable.

## 3. One ordered history

Parallel Alembic heads are resolved before merge. Context ownership does not
justify separate histories because cross-context foreign keys, deployment
ordering, and recovery still require one coherent schema version.

CI rejects:

- multiple heads;
- missing migration for model metadata changes;
- destructive operation without an approved transition;
- migration that depends on developer-local state;
- seed/content loading inside schema upgrade.

## 4. Change patterns

Use expand, backfill, validate, contract.

### Expand

Add backward-compatible structures:

- nullable column or table;
- new index using low-lock techniques;
- new enum/value strategy compatible with old code;
- dual-read/write support where needed;
- new RLS policy in a safe disabled/tested state when appropriate.

### Backfill

Populate in a resumable, observable operation:

- use stable primary-key ranges/cursors;
- commit bounded batches;
- record progress and failures;
- make reruns idempotent;
- avoid holding long transactions;
- throttle against production load;
- verify counts/hashes/invariants.

Large backfills are application jobs or controlled scripts, not a long
blocking Alembic transaction.

### Validate

Verify:

- no remaining null/invalid values;
- foreign-key candidates resolve;
- workspace ownership agrees;
- hashes/counts/reconciliation match;
- application release has stopped using old shape;
- RLS behavior passes with production-like roles.

Use PostgreSQL constraint validation patterns when they reduce lock risk.

### Contract

Only after old code cannot run:

- enforce not-null/constraints;
- remove old column/table/index;
- remove dual-write path;
- tighten policy.

Contract migrations are deployed separately from the release that first
introduces the replacement.

## 5. Transaction and lock policy

Use transactional DDL where PostgreSQL supports it. Operations that cannot run
inside a transaction, such as selected concurrent indexes, are explicitly
marked and made restart-safe.

Before production:

- estimate table scan/rewrite and lock behavior;
- set safe statement and lock timeouts;
- use concurrent index creation where appropriate;
- avoid adding a volatile default that rewrites a large table;
- avoid broad updates in one transaction;
- document maintenance requirements.

The migration runner obtains a PostgreSQL advisory lock so only one migration
task proceeds.

## 6. Deployment ordering

The production sequence is:

1. verify backup/PITR and target version;
2. run pre-deploy compatibility checks;
3. run one locked expand migration task;
4. deploy backward-compatible API and workers;
5. run/resume backfills and validation;
6. switch reads after verification;
7. observe for a defined period;
8. run contract migration in a later deployment.

Application replicas never run migrations automatically on startup.

Workers and API declare the supported schema range. Startup fails clearly if
the database is outside that range.

## 7. Rollback and recovery

Rollback has three meanings:

- **Application rollback**: deploy the prior compatible image while expanded
  schema remains.
- **Forward schema fix**: create a new migration correcting a released
  migration.
- **Data restore**: restore PostgreSQL/object data to a verified point when a
  destructive/corrupting change cannot be repaired safely.

Alembic downgrade functions are required only when they are safe and
non-deceptive. A downgrade that discards data is not an automatic production
rollback plan.

Every destructive migration requires:

- explicit approval;
- verified backup and restore procedure;
- affected row/object estimate;
- rollback/forward-fix decision;
- reconciliation query;
- communication/maintenance plan if needed.

## 8. RLS and role migration

RLS is schema behavior and is migration controlled.

Migrations must:

- create separate owner/migration and application/worker roles;
- ensure application roles do not own tables or have `BYPASSRLS`;
- create a locked-search-path, non-recursive security-definer function that
  verifies active membership/role and is owned by a controlled non-application
  role;
- enable and force RLS before granting application access to a new private
  table;
- create read/write policies for workspace data and explicit system-catalog
  reads;
- protect child tables through direct workspace scope/composite keys or a
  tested parent-bound policy;
- grant only required schema/table/sequence/function privileges;
- test absent, valid, invalid, and cross-workspace transaction context.

Security policy changes receive the same review as application authorization
changes.

## 9. Immutable/versioned data changes

Published knowledge revisions, flow versions, dataset snapshots, document
versions, and completed runs are not updated by ordinary content migrations.

Corrections create:

- a new resource revision;
- a superseding flow/content release;
- a new extraction version;
- a new dataset/transformation snapshot;
- a provenance link explaining the supersession.

If a security or legal issue requires withdrawal, mark the version withdrawn
and restrict access while preserving the minimum audit/provenance record.

## 10. Content packages

Modules, resource types, relationship rules, taxonomies, concepts, formulas,
methods, and initial flows are versioned content, not schema.

A content package contains:

- stable package ID and semantic version;
- compatible core/module ranges;
- manifest of records and stable keys;
- source/authority/license metadata;
- checksums;
- ordered dependencies;
- import validation rules;
- release notes.

Import behavior:

- idempotent for the same package/version/checksum;
- reject same version with different checksum;
- resolve references by stable key plus package/version, not environment UUID;
- allocate environment UUIDs deterministically or through an import mapping;
- publish new revisions rather than mutate prior published content;
- record a provenance activity and import result.

Production catalog imports use a controlled administrative workflow, not
ordinary workspace credentials.

## 11. Seed classes

### System content

Versioned, source-attributed content packages suitable for production.

### Bootstrap data

Minimal required platform rows such as built-in roles, permissions, resource
types, and core module manifest registrations. Bootstrap is idempotent and
versioned.

Production bootstrap ordering is:

1. schema, roles, grants, and RLS policies;
2. built-in permission identities;
3. built-in roles and role-permission mappings;
4. core resource/module/capability identities;
5. owner identity/workspace/membership through a one-time controlled command;
6. versioned system content packages;
7. workspace module installations and configuration.

The application remains unavailable if a required bootstrap release is absent
or incompatible; it does not silently invent partial defaults.

### Development seeds

Synthetic local users/workspaces and sample content. Never run automatically
in production.

### Demo/test fixtures

Small deterministic datasets and documents with redistribution rights. Tests
own their lifecycle.

Schema migrations do not create demo data.

## 12. Data backfill contract

A backfill defines:

- stable job key and code version;
- source and target schema range;
- selection/cursor strategy;
- batch size and concurrency;
- idempotency rule;
- expected counts/invariants;
- progress storage;
- retry/error quarantine;
- cancellation/resume behavior;
- validation and cleanup.

Backfills run with a least-privilege controlled role. They establish workspace
context per batch where private rows are involved. They do not bypass tenant
rules merely for convenience.

## 13. Object-store migrations

Object changes require database/object coordination.

Rules:

- never overwrite an artifact referenced by an immutable snapshot/revision;
- write and verify the new object first;
- register new blob/version and lineage;
- switch mutable pointer only after commit;
- retire old object after retention and reference checks;
- use reconciliation to find missing/orphan objects;
- record checksum before and after copies;
- preserve workspace scope and encryption metadata.

Large object transformations are durable jobs, not Alembic migrations.

Object versions and the KMS keys required to decrypt them are retained for at
least the PostgreSQL point-in-time recovery window. A lifecycle policy cannot
delete an object merely because the current database no longer references it
if a supported PITR point may still do so.

## 14. Search and projection migration

Search entries, embeddings, and denormalized read models are disposable
projections.

When their schema changes:

1. add a new projection version;
2. dual write or rebuild from authoritative data;
3. validate completeness and query behavior;
4. switch reads;
5. retire the old projection.

Rebuilding a projection never changes authoritative resource revisions.

## 15. Migration tests

CI runs:

- upgrade an empty PostgreSQL database to head;
- upgrade a sanitized snapshot of the previous release;
- verify one Alembic head;
- verify expected schemas, extensions, roles, grants, indexes, constraints,
  and policies;
- run application model/schema comparison;
- execute RLS isolation tests using application roles;
- apply each content package twice and verify idempotency;
- simulate interrupted/resumed backfill;
- verify object migration/reconciliation fixtures.

Before adopting a queue adapter with its own schema, test its full upgrade path
and rolling compatibility. Prefer wrapping/vendoring required queue SQL into
the ordered Alembic release. If that is not viable, a superseding ADR must
define one coordinated, locked secondary migration lane; application replicas
still may not migrate either schema at startup.

Release candidates additionally dry-run against production-scale schema/data
statistics where available.

## 16. PostgreSQL major upgrades

The production profile follows supported PostgreSQL releases and current
security patches. A major upgrade requires:

- extension and driver compatibility review;
- backup and restore/replication test;
- migration and numerical regression suites;
- query plan and performance comparison for critical searches/analyses;
- RLS policy/security release review;
- documented rollback/failover plan.

Application code must not depend on an unreleased PostgreSQL version.

## 17. Phase 1 migration sequence

The initial history should remain narrow:

1. required extensions, schemas, roles, and migration metadata;
2. users, identities, sessions, workspaces, memberships, roles, permissions;
3. resource namespaces/types/resources/revisions;
4. modules/releases/capabilities/installations/navigation;
5. audit and outbox;
6. RLS policies, grants, and isolation tests.

Knowledge, documents, data, flows, and research are added with the vertical
slices that implement and test them. Do not create the entire long-term schema
in the first migration.

Canonical `operation_runs` and queue-adapter schema are introduced only with
the first durable operation, after the adapter migration/recovery spike passes.

