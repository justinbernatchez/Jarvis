# JARVIS Phase 1 Foundation Report

- Status: Implementation complete; awaiting architecture-gate review
- Date: 2026-08-19
- Scope: Platform foundation only
- Finance features implemented: none

## 1. Implementation summary

Phase 1 proves the approved platform end to end:

- pnpm and uv monorepo with locked dependency graphs;
- React 19, TypeScript, and Vite workstation shell;
- FastAPI application under `/api/v1`;
- PostgreSQL development profile and real embedded PostgreSQL test fallback;
- SQLAlchemy 2 models and one ordered Alembic migration;
- OIDC Authorization Code + PKCE foundation, browser-bound atomic login state,
  owner/MFA claim enforcement, and rotating opaque HMAC-digested sessions;
- users, identities, workspaces, memberships, roles, and permissions;
- PostgreSQL row-level security with non-recursive membership functions;
- system/private resource namespaces, resource types, resources, and revisions;
- trusted module manifests, releases, capabilities, installation lifecycle, and
  configuration-driven navigation;
- portable `jarvis-config.json` export, dry-run import, and apply;
- transactional audit and outbox records;
- generated OpenAPI 3.1 contract and TypeScript client;
- automated isolation, authentication, contract, module, configuration,
  migration, and audit/outbox tests.

No CFA, Master's, paper, FRED, analytics, flow, finance, AI, semantic-search,
ML, broker, Redis, vector database, GraphQL, microservice, or Kubernetes
capability was added.

## 2. Repository tree

```text
Jarvis/
├── .github/workflows/ci.yml
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   └── src/jarvis_api/
│   │       ├── main.py
│   │       ├── dependencies.py
│   │       ├── problems.py
│   │       ├── openapi.py
│   │       ├── cli.py
│   │       └── routers/
│   └── web/
│       ├── package.json
│       ├── vite.config.ts
│       └── src/
│           ├── App.tsx
│           ├── router.tsx
│           ├── moduleRegistry.tsx
│           ├── api.ts
│           └── *.test.tsx
├── packages/
│   ├── py/jarvis-core/
│   │   ├── pyproject.toml
│   │   └── src/jarvis/
│   │       ├── core/
│   │       ├── db/
│   │       ├── identity/
│   │       ├── knowledge/
│   │       ├── platform/
│   │       ├── governance/
│   │       └── bootstrap.py
│   └── ts/api-client/
│       ├── package.json
│       └── src/
│           ├── index.ts
│           └── schema.ts
├── contracts/openapi/openapi.json
├── database/migrations/
│   ├── env.py
│   └── versions/1c3ae813911b_foundation_schema.py
├── infrastructure/docker/compose.yaml
├── tests/
│   ├── conftest.py
│   ├── test_api_contract.py
│   ├── test_audit_outbox.py
│   ├── test_authentication.py
│   ├── test_migrations.py
│   ├── test_module_configuration.py
│   └── test_security_foundation.py
├── docs/
│   ├── architecture/
│   ├── product/
│   └── phase-1/
├── alembic.ini
├── package.json
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── pyproject.toml
├── pyrightconfig.json
└── uv.lock
```

## 3. Migration list

One migration implements only the approved initial slice:

1. `1c3ae813911b_foundation_schema.py`
   - creates `identity`, `platform`, `knowledge`, and `governance` schemas;
   - separates the migration owner, non-login `jarvis_app` capability role,
     deployment-provisioned runtime login, and no-login RLS/auth definer roles;
   - creates identity/workspace/session/role/permission tables;
   - creates resource namespace/type/resource/revision tables;
   - creates module/release/capability/installation/navigation/config tables;
   - creates audit/outbox tables;
   - creates membership, session-resolution, and OIDC-provisioning functions;
   - applies and forces RLS on every private initial-slice table;
   - applies least-privilege grants, scope guards, module/release composites,
     and dependency version-range constraints.

Alembic schema-drift checking reports no uncommitted model operations.

## 4. API endpoints implemented

```text
GET    /api/v1/health
GET    /api/v1/meta/contract
GET    /api/v1/openapi.json
GET    /api/v1/docs

GET    /api/v1/auth/login
GET    /api/v1/auth/callback
GET    /api/v1/auth/session
POST   /api/v1/auth/logout
GET    /api/v1/me

GET    /api/v1/workspaces
POST   /api/v1/workspaces
GET    /api/v1/workspaces/{workspace_id}

GET    /api/v1/catalog/resources
GET    /api/v1/workspaces/{workspace_id}/resources
POST   /api/v1/workspaces/{workspace_id}/resources
GET    /api/v1/workspaces/{workspace_id}/resources/{resource_id}
PATCH  /api/v1/workspaces/{workspace_id}/resources/{resource_id}

GET    /api/v1/modules
GET    /api/v1/workspaces/{workspace_id}/modules
POST   /api/v1/workspaces/{workspace_id}/modules/{module_key}
PATCH  /api/v1/workspaces/{workspace_id}/modules/{module_key}
DELETE /api/v1/workspaces/{workspace_id}/modules/{module_key}
GET    /api/v1/workspaces/{workspace_id}/navigation

GET    /api/v1/workspaces/{workspace_id}/preferences
PUT    /api/v1/workspaces/{workspace_id}/preferences
PUT    /api/v1/workspaces/{workspace_id}/navigation-overrides
GET    /api/v1/workspaces/{workspace_id}/configuration/export
POST   /api/v1/workspaces/{workspace_id}/configuration/import/dry-run
POST   /api/v1/workspaces/{workspace_id}/configuration/import
```

## 5. Trusted module manifest example

The reviewed manifest is:

[example-module.json](../../packages/py/jarvis-core/src/jarvis/platform/manifests/example-module.json)

It declares:

- stable module ID `jarvis.example`;
- semantic release `0.1.0`;
- capability `jarvis.example.read`;
- route key `jarvis.example.home`;
- component key `jarvis.example.page`;
- navigation key `jarvis.example.nav`;
- closed JSON Schema for module configuration;
- build-provided code digest and separately checked manifest digest;
- explicit `x-jarvis-exportable=true` classification for every configuration
  property.

Registration rejects a route referencing an undeclared component or
permission. The frontend resolves `jarvis.example.page` through a static map;
database text is never used to build an import path.

## 6. Configuration export/import example

- [jarvis-config.json](examples/jarvis-config.json)
- [dry-run result](examples/configuration-import-dry-run.json)

The proof:

- exports stable module and navigation keys, not environment UUIDs;
- resolves an exact or compatible trusted module release;
- restores module configuration, enabled state, preferences, and navigation
  overrides into a second workspace;
- rejects unknown fields;
- excludes credentials, sessions, signed URLs, and private resource content.

## 7. Security test results

The complete local quality gate passed:

```text
Python tests:       29 passed
Web test files:      2 passed
Web tests:           3 passed
Ruff:                passed
Ruff format check:   passed
Pyright strict:      0 errors, 0 warnings
TypeScript checks:   passed
Oxlint:              passed
Vite production:     passed
```

Security-critical coverage includes:

- unauthenticated RFC 9457 responses;
- opaque session resolution, CSRF, Origin validation, logout, and revocation;
- OIDC PKCE challenge, encrypted verifier/nonce, signed ID-token claims,
  owner/MFA/`azp`/nonce/audience/auth-time checks, browser binding, concurrent
  single-use state, failure consumption, and old-session rotation;
- separate personal workspace bootstrap for the first OIDC identity;
- two-workspace API and direct-RLS isolation;
- cross-workspace composite-FK rejection;
- system resource visibility and private resource isolation;
- trusted manifest capability/reference validation;
- configuration import compatibility and credential exclusion;
- serialized configuration imports, coordinated upgrades, direct re-enable
  dependency validation, and database-enforced dependency release/range
  integrity;
- transactional rollback/commit behavior for audit and outbox.

## 8. RLS isolation results

Gate A passed:

- User A cannot address Workspace B through the API.
- User B receives no result for User A's private resource.
- the API connects through a non-owner runtime login that has no table access
  until it explicitly assumes `jarvis_app`;
- A direct SQLAlchemy transaction under `SET LOCAL ROLE jarvis_app` sees
  system resources and Workspace A resources, but not Workspace B resources.
- `jarvis_app` is `NOSUPERUSER` and `NOBYPASSRLS`.
- all 15 private initial-slice tables have RLS enabled and forced;
- no-login definer roles own only the audited membership/session/provisioning
  functions required to cross RLS safely.
- a private resource revision using another workspace ID fails its composite
  foreign key.

Gate B passed:

- the system `system.core` namespace and foundation resource are readable to
  both users;
- private resources remain workspace scoped;
- private ownership is stored as `workspace_id`;
- `created_by_user_id` records attribution and does not define tenant scope.

## 9. Migration test results

The complete chain was run against a newly created real PostgreSQL database:

```text
empty database -> alembic upgrade head -> success
already migrated database -> alembic upgrade head -> no-op success
head -> downgrade base -> upgrade head -> success
alembic check -> no model/schema drift
```

Local tests use real embedded PostgreSQL 17.9 because the implementation host
has no Docker/system PostgreSQL. The committed Compose and CI profiles use the
approved PostgreSQL 18.6 target. This implementation choice is documented in
[ADR-0011](../architecture/decisions/0011-embedded-postgresql-tests.md).

## 10. OpenAPI and client-generation results

- FastAPI generates [openapi.json](../../contracts/openapi/openapi.json).
- All product endpoints are under `/api/v1`.
- OpenAPI includes UUID, RFC 3339, decimal-string, optimistic-lock, pagination,
  and RFC 9457 schemas.
- `openapi-typescript` generates
  [schema.ts](../../packages/ts/api-client/src/schema.ts).
- the runtime wrapper uses `openapi-fetch<paths>`, so paths, parameters,
  headers, bodies, and responses remain generated-contract typed.
- generation is deterministic and included in CI drift checks.

Contract tests verify:

- canonical lowercase UUID strings;
- timezone-aware RFC 3339 timestamps;
- decimal response value `"0.05000"`;
- opaque cursor pagination;
- ETag/`If-Match` optimistic locking and `412` stale writes;
- `application/problem+json` errors.

## 11. Audit/outbox demonstration

Installing `jarvis.example` executes one database transaction containing:

- the module installation state change;
- an `audit_events` row with action `module.install`;
- an `outbox_events` row with event
  `platform.module_installed.v1`.

The integration test verifies both rows commit together. A second test forces a
transaction exception and verifies neither audit nor outbox evidence remains.
No broker or dispatcher was introduced because Phase 1 has no background-job
requirement.

## 12. Known limitations

- A live managed OIDC provider has not been selected or exercised; the OIDC
  protocol path is tested with signed local keys and mocked HTTP endpoints.
- Local database tests run PostgreSQL 17.9; PostgreSQL 18.6 remains the CI,
  Compose, and production release gate.
- The outbox is durable and transactional, but no dispatcher is needed or
  implemented in this phase.
- Persistent `Idempotency-Key` storage is deferred because this slice has no
  durable job/create retry protocol; identical module/configuration state is
  naturally idempotent.
- Audit rows are append-oriented but not cryptographically tamper-evident.
- Dependency behavior is proven with a test-only dependent manifest; only the
  neutral `jarvis.example` manifest is shipped as a user-visible module.
- Compatible configuration fallback is intentionally limited to a registered
  release in the same semantic major version.
- Resource registry content is only a neutral foundation record; no finance or
  curriculum content exists.
- Object storage, encrypted user credentials, background jobs, and production
  secret/KMS integration are deferred until a scoped feature requires them.
- Production backup/restore, load, and external penetration tests remain
  deployment gates rather than local Phase 1 proofs.

## 13. Unresolved Phase 0 risks

The Phase 1 slice materially addresses AR-001 (RLS), AR-002 (OIDC foundation),
AR-003 (API scalar encoding), and AR-011 (typed platform abstractions), but
their controls must be repeated for each new table/client/provider.

Still unresolved or intentionally deferred:

- **AR-002**: select and validate the production OIDC provider.
- **AR-003**: define analytical JCVE vectors when dataset/flow values exist.
- **AR-004**: select/spike a durable queue only when the first durable job is
  approved.
- **AR-005**: PDF parser security, quality, and licensing.
- **AR-006**: historical execution-image retention and rerun semantics.
- **AR-007**: cross-store/KMS disaster-recovery drill.
- **AR-008**: CFA, university, paper, market-data, and provider licensing.
- **AR-009**: point-in-time provider/vintage correctness.
- **AR-010**: AI evidence, prompt injection, and provider privacy.
- **AR-011**: prove module/resource abstractions with real knowledge content
  and later three independent flows.
- **AR-012**: production RPO/RTO, performance, resilience, and cost evidence.

## 14. Recommendation for Phase 2

After Phase 1 approval, Phase 2 should implement only the structured knowledge
layer:

1. generic taxonomies and hierarchy traversal;
2. typed concept, definition, formula, and method revisions;
3. source authority, citations, and relationship rules;
4. database-driven CFA and Master's hierarchy shells without bulk content;
5. lexical theory search;
6. content administration/import packages;
7. one small, licensed seed set proving system content plus workspace notes.

Phase 2 should reuse the current resource, module, workspace, audit, outbox,
OpenAPI, and RLS foundations. It should not introduce FRED, documents,
analytics flows, finance calculations, semantic search, or AI automatically.

