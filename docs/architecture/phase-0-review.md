# JARVIS Phase 0 Review

- Status: Complete for architecture baseline
- Date: 2026-08-18
- Scope reviewed: product specification, architecture proposal, data model,
  platform contracts, assurance strategies, and ADR-0001 through ADR-0010

## 1. Outcome

The repository was a greenfield placeholder with only a two-line README.
Phase 0 now provides an internally reviewed architecture baseline for all 20
deliverables requested by the master specification.

No application scaffold or feature code was created. Phase 1 can use these
documents as decision inputs, but every phase gate below remains enforceable.

## 2. Deliverable coverage

### 1. Recommended technology stack

Covered by [Architecture proposal](architecture-proposal.md), sections 1, 2,
and 5, plus:

- [ADR-0002: Vite workstation](decisions/0002-vite-workstation.md)
- [ADR-0003: PostgreSQL](decisions/0003-postgresql-primary-store.md)
- [ADR-0009: durable jobs](decisions/0009-postgresql-backed-jobs.md)

Decision: React/TypeScript/Vite, FastAPI/Pydantic/SQLAlchemy/Alembic,
PostgreSQL 18, S3-compatible storage, Python analytics, OpenAPI, pnpm, uv, and
Docker.

### 2. Application architecture

Covered by proposal sections 3 and 4 and
[ADR-0001](decisions/0001-modular-monolith.md).

Decision: modular monolith with separate static web, API process, and worker
process. Contexts communicate through public facades or typed events.

### 3. Database ERD

Covered by [Data model](data-model.md), section 4.

The ERD is conceptual until translated into tested Alembic migrations. It
includes identity/workspaces, resources/revisions, modules, knowledge,
documents, datasets, flows, research, operations, and provenance.

### 4. Core entities

Covered by data model sections 5 through 16.

The shared resource registry is deliberately thin. Typed subtype tables avoid
EAV, and canonical operation runs avoid unrelated ad hoc run APIs.

### 5. Relationships

Covered by data model sections 8, 9, 15, and 17.

Graph edges use allowed type/predicate/type rules. Evidence, artifacts, and
provenance use target-specific junction tables with real foreign keys rather
than generic polymorphic IDs.

### 6. Module system

Covered by proposal section 8,
[ADR-0005](decisions/0005-trusted-module-manifests.md), data model section 10,
and [Platform contracts](platform-contracts.md), section 3.

Trusted code manifests declare executable capabilities; workspace/database
configuration controls installation, navigation, labels, and settings.

### 7. Flow engine architecture

Covered by proposal section 9,
[ADR-0006](decisions/0006-versioned-flow-dsl.md), data model section 13, and
platform contracts sections 5 and 6.

Mutable drafts publish immutable, compiled, versioned DAGs of allowlisted
handlers. Arbitrary code is excluded.

### 8. Data-provider architecture

Covered by proposal section 10, data model section 12, and platform contracts
section 7.

Provider-import orchestration captures raw evidence and materializes immutable
snapshots. Analytical handlers cannot call providers directly.

### 9. Document-processing architecture

Covered by proposal section 11, data model section 11, platform contracts
section 8, and [Threat model](threat-model.md), section 8.

Untrusted uploads remain in quarantine until a no-egress verifier succeeds.
Extraction is page aware, versioned, and isolated from provider-enabled
workers.

### 10. AI/tool architecture

Covered by proposal section 12, platform contracts sections 8 and 9, data
model AI records, and threat model section 11.

AI is read-only first, evidence backed, provider neutral, and unable to bypass
application authorization or deterministic engines.

### 11. Authentication architecture

Covered by proposal section 13 and
[ADR-0008](decisions/0008-oidc-and-server-sessions.md).

OIDC Authorization Code with PKCE creates a server-side opaque session under a
same-origin API. Identity uses `(issuer, subject)`.

### 12. Security model

Covered by proposal section 14 and the complete threat model.

The model includes identity/session, workspace isolation, secrets, uploads,
providers, flows/jobs, AI, supply chain, availability, privacy, verification
gates, residual risk, and incident response.

### 13. Folder structure

Covered by proposal section 15.

The structure separates apps, TypeScript/Python packages, contracts,
migrations/content, docs, infrastructure, and cross-cutting tests.

### 14. Testing strategy

Covered by [Testing strategy](testing-strategy.md) and
[Numerical correctness policy](numerical-correctness.md).

It includes unit/property/integration/contract/E2E/security/migration/
resilience tests, numerical golden vectors, adapter conformance, exact-release
security gates, and a Windows tooling smoke job.

### 15. Migration strategy

Covered by [Migration strategy](migration-strategy.md).

One Alembic history uses expand/backfill/validate/contract. Content packages,
backfills, object migrations, RLS roles, bootstrap ordering, and queue-adapter
migrations are separate controlled concerns.

### 16. Deployment strategy

Covered by [Deployment strategy](deployment-strategy.md).

Local Compose and a portable managed production profile are defined. The AWS
mapping is a reference, not a domain dependency. Kubernetes is deferred.

### 17. MVP scope

Covered by proposal section 19.

The Yield Curve journey is the first implementation increment, not the full
MVP. MVP completion also requires:

- database-driven CFA and Master's hierarchies;
- basic concepts, definitions, formulas, and search;
- basic paper upload/library/metadata/notes;
- FRED and saved datasets;
- generic flow engine with Yield Curve, Macro Time-Series, and Equity DCF
  conformance flows;
- module/settings/navigation/configuration portability;
- read-only evidence-backed contextual JARVIS.

This reconciles the narrow risk-reducing vertical slice with the master
specification's broader MVP definition.

### 18. Future scalability

Covered by proposal section 21 and ADR-0001 extraction criteria.

Horizontal API/worker scaling, observation partitioning, projections, and
measured extraction seams are defined without premature services.

### 19. Major architectural risks

Covered by proposal section 22, threat model residual risks, and the risk
register below.

### 20. Recommended implementation sequence

Covered by proposal section 20.

The sequence establishes identity/platform, knowledge, data, one integrated
flow, documents, remaining proof flows, and only then AI/deeper modules.

## 3. Deliberate specification interpretations

### Vite instead of Next.js

Next.js was a candidate, not a requirement. The authenticated workstation has
no near-term SSR/SEO need, and Vite preserves one backend business-logic
boundary. Revisit only for measured public rendering needs.

### Workspace instead of direct user ownership

`workspace_id` defines private ownership; user IDs record actors. This is a
stronger path to the specification's future multi-user/collaboration goal.

### In-process Python engines plus worker

The analytics “service” begins as pure Python packages executed in the API for
short work and the worker for heavy/durable work. It does not start as a
separate HTTP microservice. The port/package boundary permits extraction when
resource isolation or scaling requires it.

### One golden path before the complete MVP

Yield Curve Analysis is the first deployable architecture proof. The MVP is not
declared complete until all three proof flows and the remaining listed
foundation/theory/paper/data capabilities exist.

### PostgreSQL-backed job adapter is conditional

PostgreSQL queueing is the accepted direction, but Procrastinate remains a
candidate until its migrations, rolling upgrades, stalled recovery,
dead-letter behavior, and conformance suite pass. This prevents a library
choice from violating the one controlled migration process.

## 4. Product capabilities intentionally deferred

The architecture supports but does not yet specify feature-level UX/domain
rules for:

- dashboard widget catalog;
- visual Flow Builder;
- quantitative Method Selector;
- accounting adjustment and GAAP/IFRS rule engine;
- full three-panel research workstation behavior;
- internal content-management UI;
- structured analysis report templates/export;
- semantic graph visualization;
- plugin marketplace;
- non-finance modules.

These are not Phase 0 blockers. Each receives a feature architecture,
data/migration change, threat/numerical review where applicable, and acceptance
tests before implementation.

## 5. Architecture risk register

### AR-001: RLS implementation correctness

- Severity: high
- Blocks: first private production schema
- Risk: policy recursion, missing child-table scope, unsafe role ownership, or
  stale transaction context could leak workspace data.
- Gate: implement the non-recursive membership function, role/grant model, and
  two-workspace tests before granting application access.
- Owner: Identity/Data architecture
- Revisit: every private table or authorization-model change

### AR-002: OIDC provider and session conformance

- Severity: high
- Blocks: login deployment
- Risk: issuer/JWKS/claim/state/PKCE/MFA mistakes can enable account takeover.
- Gate: select a conformant provider and pass the exact-release OIDC/session/
  CSRF suite with the documented same-origin routes.
- Owner: Identity/Security
- Revisit: provider or client-type change

### AR-003: Canonical encoding across Python and TypeScript

- Severity: high
- Blocks: analytical flow idempotency and semantic hashes
- Risk: different decimal, float, timestamp, or table serialization produces
  false cache/idempotency/reproducibility results.
- Gate: version JCVE, publish cross-language golden vectors, and distinguish
  byte from semantic dataset hashes.
- Owner: Analytics/Contracts
- Revisit: new value/artifact type or encoding version

### AR-004: Durable queue adapter

- Severity: high
- Blocks: first durable ingestion/analysis pipeline
- Risk: adapter migrations, lease recovery, stale workers, dead letters, and
  OLTP contention may violate release or correctness requirements.
- Gate: adapter spike and contract tests for outbox dispatch, fencing,
  cancellation, recovery, migration, retention, and rolling compatibility.
- Owner: Platform/Operations
- Revisit: first durable job and measured queue contention

### AR-005: PDF extraction security and quality

- Severity: high
- Blocks: document ingestion
- Risk: native parser exploits, resource bombs, licensing constraints, OCR
  errors, or page locator drift.
- Gate: representative corpus benchmark, license/security review, no-egress
  sandbox, malformed-file tests, and citation-version tests.
- Owner: Documents/Security
- Revisit: parser/OCR release or new document type

### AR-006: Exact rerun implementation retention

- Severity: medium-high
- Blocks: claiming `exact` historical rerun
- Risk: handler digest exists but executable image is missing, vulnerable, or
  incompatible with current infrastructure.
- Gate: define image retention/support window, capability routing, drain
  behavior, and replay/current-rerun UX before promising exact rerun.
- Owner: Analytics/Operations
- Revisit: release retention or critical vulnerability

### AR-007: Cross-store disaster recovery

- Severity: high
- Blocks: production readiness
- Risk: PostgreSQL, object versions, KMS keys, queue/outbox state, and external
  side effects restore to inconsistent points.
- Gate: perform the documented quiesced restore/reconciliation drill and
  measure RPO/RTO before production declaration.
- Owner: Operations/Security
- Revisit: storage/KMS/provider/topology change

### AR-008: Content and data licensing

- Severity: high
- Blocks: distributing/importing affected content
- Risk: CFA, university, research-paper, market-data, PDF-parser, or AI terms
  may restrict storage, extraction, sharing, or derived output.
- Gate: source/license metadata and legal/product review for every production
  content/provider package.
- Owner: Product/Governance
- Revisit: each source/provider/license change

### AR-009: Point-in-time data correctness

- Severity: high
- Blocks: historical/backtest claims
- Risk: latest-revised FRED data creates look-ahead bias.
- Gate: preserve ALFRED real-time periods/vintages and label snapshot
  backtest-safety before historical claims.
- Owner: Data/Analytics
- Revisit: each provider/method

### AR-010: AI evidence and provider privacy

- Severity: high
- Blocks: AI tools
- Risk: prompt injection, unsupported citations, cross-workspace retrieval, or
  provider retention leaks data.
- Gate: read-only tools, evidence validation, adversarial tests, and approved
  provider retention/redaction policy.
- Owner: AI/Security
- Revisit: each model/tool/provider change

### AR-011: Scope and abstraction pressure

- Severity: high
- Blocks: declaring the platform abstractions stable
- Risk: generic resource/flow/module layers become EAV/giant JSON or require
  flow-specific branches.
- Gate: typed tables and all three conformance flows without engine branches.
- Owner: Architecture
- Revisit: each proof flow and module

### AR-012: Unproven operational targets

- Severity: medium
- Blocks: production SLO claim
- Risk: RPO/RTO, performance, cost, and queue capacity are design targets, not
  observed behavior.
- Gate: restore, load, and resilience measurements with recorded budgets.
- Owner: Operations
- Revisit: production topology or workload change

## 6. Non-blocking deferred decisions

These do not block Phase 1 scaffolding:

- specific managed OIDC vendor;
- container PaaS versus AWS reference deployment;
- observability/error-tracking vendor;
- exact PDF/OCR library;
- `pgvector` and embedding provider;
- dedicated broker/workflow system;
- dedicated analytics/search/document services;
- desktop/mobile bearer-token client;
- multi-region topology;
- Kubernetes.

They do block their corresponding production feature when a risk-register gate
requires a concrete choice.

## 7. Review corrections incorporated

The final baseline explicitly resolves earlier documentation ambiguities:

- common `operation_runs` back the generic status API;
- mutable flow drafts are separate from immutable published versions;
- version names distinguish optimistic, revision, semantic, storage, and
  attempt versions;
- module capabilities have stable identities and per-release declarations;
- dependency ranges resolve to exact active releases;
- evidence/provenance/artifacts use typed foreign-key junctions;
- multi-page chunks use explicit page spans;
- analytical handlers cannot bypass dataset materialization through providers;
- historical rerun modes and bundle availability are explicit;
- document structural validation occurs in the sandbox, not the API;
- outbox dispatch, attempt fencing, and queue migration gates are explicit;
- JCVE defines semantic hashing;
- cross-store/KMS recovery is a coordinated drill;
- core security tests gate the exact release and Windows tooling is smoke
  tested.

## 8. Phase 0 exit criteria

Phase 0 documentation is complete because:

- the master specification is versioned in the repository;
- all 20 requested architecture deliverables have an identified document;
- major decisions are recorded in ADRs;
- the data model, contracts, security, numerical, testing, migration, and
  deployment baselines agree on their core boundaries;
- known risks have phase-specific owners, gates, and revisit triggers;
- no application implementation was started before architecture review.

Phase 1 should begin with repository hygiene/tooling and the identity/platform
foundation. It must not treat later-phase risk gates as already satisfied.

