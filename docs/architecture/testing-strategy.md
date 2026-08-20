# JARVIS Testing Strategy

- Status: Phase 0 baseline
- Date: 2026-08-18

## 1. Quality objective

Testing must demonstrate more than a working UI. A feature is complete only
when its database, application service, API, validation, error handling,
authorization, tests, and documentation are appropriate to its risk.

Analytical features additionally require:

- reproducibility;
- audit/provenance records;
- authoritative numerical tests;
- diagnostics and limitations;
- evidence that the UI and AI present engine output without changing it.

## 2. Test layers

### Unit tests

Fast and isolated tests cover:

- domain value objects and invariants;
- formula and transformation functions;
- finance/statistics engines;
- flow DSL parsing and compilation;
- handler behavior with fake scoped ports;
- permission decisions;
- API DTO validation and error mapping;
- frontend components, hooks, formatting, and accessibility behavior.

Unit tests do not mock the function under test or assert implementation trivia.

### Property and metamorphic tests

Hypothesis exercises valid/invalid domains and mathematical invariants.
Metamorphic tests verify expected relationships when a perfect oracle is hard
to obtain, such as scaling cash flows or shifting a time series.

### Integration tests

Use real disposable dependencies through containers:

- PostgreSQL 18 with production extensions and RLS;
- S3-compatible storage;
- durable queue tables/worker;
- OIDC test issuer or standards-conformant local fixture;
- mocked HTTP servers at external provider boundaries.

Integration tests verify migrations, constraints, transactions, outbox,
idempotency, signed-object authorization, search, and adapter behavior.
SQLite is not a substitute for PostgreSQL integration tests.

### Contract tests

Contract suites cover:

- normalized OpenAPI generation and breaking-change detection;
- generated TypeScript client compatibility;
- module manifest schema/dependency resolution;
- flow DSL/compiler and handler I/O schemas;
- data-provider capability conformance;
- blob, secret, job, extractor, and AI provider ports;
- event schema compatibility;
- document citation locators and artifact manifests.

Every new adapter must pass the shared port conformance suite.

### End-to-end tests

Playwright covers critical user journeys through the real browser, API,
PostgreSQL, and object store. The first required journey is:

1. authenticate as the invited owner;
2. enter the personal workspace;
3. browse the seeded Yield Curve concept and related formula;
4. retrieve a recorded FRED fixture and save a dataset snapshot;
5. run Yield Curve Analysis;
6. inspect diagnostics and provenance;
7. save the analysis into a project;
8. upload a paper fixture and open a page citation;
9. ask the read-only assistant for an evidence-backed explanation.

E2E tests remain few and high value. Lower layers cover combinatorial behavior.

### Security and adversarial tests

Mandatory suites include:

- OIDC state, nonce, PKCE, redirect, session rotation, and revocation;
- cookie flags, Origin, CSRF, and open-redirect behavior;
- two-workspace API, SQL, search, relationship, object, cache, export, and
  worker isolation;
- absence/failure of RLS transaction context;
- role and permission matrix;
- malicious module/flow keys and expression ASTs;
- oversized/malformed uploads and parser timeouts;
- provider SSRF and hostile response fixtures;
- secret/log/config-export redaction;
- prompt injection, unauthorized AI tool calls, and unsupported citations;
- spreadsheet formula injection on export.

### Migration tests

CI verifies:

- create schema from an empty database;
- upgrade from the last released schema and supported snapshots;
- constraints/indexes/RLS are present;
- migration and application model agree;
- idempotent content packages can be reapplied;
- a migration lock prevents concurrent execution;
- data backfills resume safely.

Downgrade scripts may be tested where safe, but production recovery relies on
forward fixes and backups rather than destructive automatic rollback.

### Performance and resilience tests

Before production exposure, establish budgets for:

- API latency for common reads;
- global search latency and result limits;
- table/chart rendering with representative row counts;
- FRED import throughput and rate-limit behavior;
- PDF extraction time/memory/page limits;
- flow queue delay and step duration;
- worker/database connection usage;
- analytics cancellation and timeout;
- backup/restore duration.

Load tests target defined hypotheses; they are not a vanity request count.
Chaos/recovery tests terminate workers during idempotent jobs and verify
correct retry/recovery.

## 3. Numerical testing

The [Numerical correctness policy](numerical-correctness.md) is normative.

Required categories:

- authoritative golden vectors with source and conventions;
- independent cross-checks for critical calculations;
- property tests and edge cases;
- tolerance and convergence assertions;
- known statistical datasets and reference outputs;
- time-aware split/leakage tests;
- dependency-upgrade regression suites;
- reproducibility fingerprint and artifact-hash assertions.

A test cannot widen tolerance merely to accommodate unexplained drift.

## 4. Tooling

Python:

- pytest;
- Hypothesis;
- pytest-asyncio;
- coverage.py;
- Pandera for dataset/dataframe contracts;
- Testcontainers for PostgreSQL and S3-compatible integration;
- time-freezing only through explicit injected clocks.

Web:

- Vitest;
- React Testing Library;
- user-event;
- axe-based accessibility checks;
- Playwright.

Static verification:

- strict TypeScript;
- Python type checking;
- lint and format checks;
- architecture/import-boundary checks;
- OpenAPI and JSON Schema validation;
- dependency, secret, license, source, and container scans.

Exact tools are pinned in lockfiles when scaffolding occurs. Test semantics,
not tool brands, are the durable contract.

## 5. Test organization

Recommended locations:

```text
apps/web/src/**/*.test.tsx
packages/ts/*/src/**/*.test.ts
packages/py/*/tests/unit/
packages/py/*/tests/property/
tests/integration/
tests/contracts/
tests/security/
tests/e2e/
tests/fixtures/
tests/golden/
```

Tests should live near code when they are unit-focused and in top-level suites
when they cross packages/processes.

## 6. Fixtures and test data

Use synthetic or redistributable fixtures only.

Fixture rules:

- no production documents, credentials, prompts, or personal finance data;
- record external HTTP fixtures after redaction and licensing review;
- include FRED examples with current and vintage observations;
- include small valid, malformed, encrypted, scanned, and adversarial PDF
  fixtures;
- identify source and expected license for every research/numerical fixture;
- make generated random data deterministic by seed;
- immutable fixture hashes detect accidental changes;
- large performance fixtures are generated or stored outside normal Git when
  appropriate.

Golden output changes require review explaining why the prior expected result
was wrong or why an approved algorithm/version changed.

## 7. Workspace-isolation test pattern

Every private-resource integration suite creates:

- Workspace A with Owner A;
- Workspace B with Owner B;
- one system catalog resource;
- similar private resources in both workspaces.

It verifies:

- A can access A and allowed system data;
- A cannot read, infer, link, mutate, execute, export, search, or sign a URL
  for B;
- missing workspace context fails closed;
- a worker job scoped to A cannot consume a B resource ID;
- elevated fixtures are not accidentally used by normal application tests.

This suite runs against the same database role configuration used by the
application.

## 8. Provider conformance

Each data-provider adapter is tested for:

- capability declaration;
- connection success/failure;
- search pagination;
- metadata and units;
- missing/revised observations;
- vintages/availability where supported;
- raw response capture and hash;
- rate limiting and retry hints;
- timeout/unavailable/malformed response translation;
- credential redaction;
- stable normalized output.

Network-independent recorded fixtures run on every PR. A small live-provider
suite runs manually or on a protected schedule with non-production
credentials; live provider availability does not gate ordinary PRs.

## 9. Flow conformance

Compiler tests cover:

- schema-valid and invalid definitions;
- unknown/uninstalled handler;
- incompatible ports;
- missing permissions;
- cycles and graph limits;
- invalid restricted expressions;
- secret literal detection;
- unsupported DSL/handler version;
- deterministic classification.

Runtime tests cover:

- successful DAG execution;
- waiting for user input;
- cancellation;
- retryable and terminal failures;
- worker crash and redelivery;
- outbox dispatch loss/recovery and `pending_dispatch` state;
- stale-worker fencing after lease loss;
- permission revocation between enqueue and side effect;
- idempotent side effects;
- exact version/snapshot pinning;
- warning propagation;
- artifact size/reference behavior;
- provenance completeness.

Yield Curve, Macro Time-Series, and Equity DCF are conformance fixtures. The
engine must not contain branches keyed to those flow IDs.

## 10. Document and citation tests

Verify:

- original checksum and object version;
- MIME/signature/size/page validation;
- quarantine and finalization;
- parser timeout and resource limits;
- page numbering and text/chunk locators;
- citation quote/hash validation;
- reprocessing creates a new extraction version;
- old citations still resolve to their pinned extraction;
- failed ingestion does not publish partial searchable content;
- authorization applies to upload, processing status, search, and download.

## 11. AI tests

Before enabling AI:

- tool schemas and required permissions are tested;
- evidence IDs and citations resolve to authorized immutable sources;
- model output cannot create an authoritative calculation;
- read-only tools reject mutation attempts;
- tool calls recheck membership after session/role changes;
- prompt-injected documents cannot access secrets or other tools;
- unsupported citation/result claims are flagged or refused;
- model/provider/version and tool provenance are persisted;
- provider payloads observe configured redaction/retention policy.

Model-output exact text is not a stable test oracle. Assert structured
properties, evidence, authorization, refusal behavior, and safe boundaries.

## 12. CI stages

### Pull request fast gate

- format and lint;
- strict type checks;
- unit/property/component tests;
- manifest/flow/schema validation;
- OpenAPI generation and client drift;
- canonical value-encoding/hash vectors shared by Python and TypeScript;
- secret/dependency/source scans.

### Pull request integration gate

- PostgreSQL/object-store integration;
- migrations from empty and previous release;
- RLS/cross-workspace suite;
- OIDC/session/CSRF suite;
- operation/outbox/queue migration and fencing suite when jobs are present;
- adapter contracts;
- selected Playwright golden path;
- container build.

### Main/release gate

- complete E2E and numerical regression;
- image and license scan;
- SBOM generation;
- migration dry run against release-like backup;
- signed/versioned artifacts;
- deployment smoke tests.

These gates run on the exact release commit/artifacts. Security evidence from a
different commit or an earlier schedule cannot authorize deployment.

### Protected scheduled/manual gate

- live external-provider smoke tests;
- extended performance/resilience;
- backup restore;
- dependency-upgrade numerical comparison;
- extended fuzz/security cases that supplement, but never replace, core
  OIDC/session/RLS/cross-workspace release gates.

CI includes a Windows smoke job for documented root install/check commands.
Phase-specific required-test manifests declare which E2E/security/numerical
suites gate Foundation, Data, Documents, Flows, and AI releases; a feature
cannot ship by omitting its suite from a generic pipeline.

## 13. Coverage policy

Coverage is a diagnostic, not the definition of quality.

- No blanket percentage can replace required risk tests.
- Critical finance, authorization, flow compiler, and provenance branches must
  have direct tests.
- New untested lines/branches require justification.
- Exclusions are narrow and reviewed.
- Mutation testing may be introduced for finance/authorization code if normal
  coverage fails to demonstrate assertion strength.

## 14. Flake policy

A flaky test is a defect.

- Do not use arbitrary sleeps.
- Await observable state with bounded deadlines.
- Control clocks, seeds, ports, and external responses.
- Preserve traces/screenshots/logs with secret redaction on failure.
- Quarantine is temporary, owned, and time-bounded; quarantined critical
  security/numerical tests block release.

## 15. Completion criteria

A feature can be marked done only when:

- acceptance and failure cases are automated at the right layers;
- new database changes have migration/upgrade tests;
- private data has workspace-isolation tests;
- provider/handler/port changes pass conformance suites;
- documentation and contract artifacts are current;
- no introduced lint/type/test/security failures remain;
- known limitations and residual risks are recorded.

