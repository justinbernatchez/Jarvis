# JARVIS Platform Contracts

- Status: Phase 0 baseline
- Date: 2026-08-18
- Related decisions:
  [trusted modules](decisions/0005-trusted-module-manifests.md),
  [flow DSL](decisions/0006-versioned-flow-dsl.md), and
  [OpenAPI](decisions/0010-openapi-contract.md)

## 1. Purpose

This document defines the boundaries that make JARVIS a platform rather than a
collection of finance pages. The examples are normative design inputs, not
generated production schemas. Implementation must publish machine-readable
JSON Schema/OpenAPI artifacts and conformance tests.

The contracts cover:

- trusted module manifests and workspace installation;
- HTTP API conventions;
- authored and compiled flow definitions;
- flow handler execution;
- data-provider capabilities;
- storage, secret, job, document, and AI ports;
- domain events and compatibility.

## 2. Contract principles

1. Data selects trusted behavior; it never supplies executable code.
2. Contracts are versioned independently from implementation packages.
3. Published definitions are immutable.
4. Inputs and outputs are validated at every process boundary.
5. Workspace and actor context are established by authorization, not payload
   ownership fields.
6. Provider-specific DTOs stop at provider adapters.
7. Long-running work is addressable through durable run resources.
8. Every execution can identify exact code, configuration, data, and artifact
   versions.
9. Backward-compatible additions are preferred; breaking changes require a
   new contract major version and migration path.

## 3. Module manifest

### 3.1 Trust boundary

A module manifest is packaged with reviewed application code. The application
loads it from an installed package, validates it, and reconciles its
declarative metadata into the platform tables.

A database row may reference keys from the manifest. It may not provide:

- Python or JavaScript module paths;
- executable expressions outside the restricted JARVIS expression grammar;
- SQL or shell commands;
- remote code URLs;
- unregistered component, handler, provider, or AI tool names.

### 3.2 Manifest shape

```json
{
  "manifestVersion": "1.0",
  "id": "finance.fixed_income",
  "version": "0.1.0",
  "name": "Fixed Income",
  "description": "Fixed-income theory and analytical workflows.",
  "coreCompatibility": ">=0.1.0 <1.0.0",
  "dependencies": [
    {
      "moduleId": "jarvis.knowledge",
      "version": ">=0.1.0 <1.0.0"
    },
    {
      "moduleId": "jarvis.flows",
      "version": ">=0.1.0 <1.0.0"
    }
  ],
  "permissions": [
    "fixed_income.read",
    "fixed_income.edit",
    "fixed_income.execute"
  ],
  "routes": [
    {
      "key": "fixed_income.home",
      "path": "/research/fixed-income",
      "componentKey": "fixed_income.overview",
      "requiredPermission": "fixed_income.read"
    }
  ],
  "navigation": [
    {
      "key": "fixed_income.nav",
      "parentKey": "research.nav",
      "routeKey": "fixed_income.home",
      "label": "Fixed Income",
      "iconKey": "chart-line",
      "defaultOrder": 300
    }
  ],
  "components": [
    {
      "key": "fixed_income.overview",
      "kind": "page"
    }
  ],
  "flowHandlers": [
    {
      "key": "fixed_income.yield_curve_metrics",
      "version": "1.0.0"
    }
  ],
  "dataProviders": [],
  "aiTools": [
    {
      "key": "fixed_income.search_theory",
      "version": "1.0.0"
    }
  ],
  "configurationSchema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
      "defaultCurve": {
        "type": "string"
      }
    },
    "additionalProperties": false
  }
}
```

### 3.3 Stable keys

- Module IDs use reverse-domain-like lowercase dotted identifiers.
- Route, component, handler, provider, permission, and tool keys are globally
  unique stable capability identities prefixed by the owning module.
- Manifest keys are stable across releases. Renaming requires an alias and a
  migration.
- A release declares implementations of stable capability identities; the
  same owner is expected to reuse a key across releases.
- Human labels are configurable and are not identifiers.
- Icon keys resolve to the project-owned icon registry.

### 3.4 Installation

Installation is a transaction:

1. Validate manifest schema and signature/source trust.
2. Verify core compatibility and dependency constraints.
3. Verify capability-key uniqueness.
4. Register the immutable module release and its capability declarations.
5. Validate workspace configuration against the release schema.
6. Resolve every dependency range to an exact installed release.
7. Create or update a workspace installation.
8. Rebuild navigation/search projections through outbox events.

Removing a module disables routes and execution. It does not delete user data
or immutable historical references. A release cannot be removed while a
published flow or completed run pins it.

A workspace has at most one active release per module ID. Side-by-side
historical releases may remain retained for evidence/execution bundles, but
they are not simultaneously active in navigation/configuration.

### 3.5 Frontend registry

The web bundle contains a static registry:

```text
component key -> lazy import factory
route key -> route metadata
icon key -> icon component
```

Unknown keys fail closed with a configuration error. They never trigger a
dynamic import assembled from database text.

### 3.6 Configuration export and import

`jarvis-config.json` is a versioned portability contract:

```json
{
  "schemaVersion": "1.0",
  "exportedAt": "2026-08-18T22:00:00Z",
  "coreCompatibility": ">=0.1.0 <1.0.0",
  "modules": [
    {
      "id": "finance.fixed_income",
      "version": "0.1.0",
      "enabled": true,
      "configuration": {}
    }
  ],
  "navigationOverrides": [],
  "preferences": {},
  "workflowDefaults": {},
  "personalCategories": []
}
```

Exports use stable keys, not environment UUIDs. They exclude sessions,
credential values/references, signed URLs, documents, datasets, and other
private content unless a separate resource export is requested.

Import first returns a dry-run plan with compatible installs/updates, ignored
fields, unresolved dependencies, and settings requiring user choice.
Application requires explicit confirmation and applies the validated plan
transactionally where possible. Credentials are configured separately.

## 4. HTTP API contract

### 4.1 Base and scope

All endpoints use `/api/v1`.

Recommended scope:

- `/api/v1/me` for the current profile and memberships;
- `/api/v1/workspaces/{workspace_id}/...` for private resources;
- `/api/v1/catalog/...` for shared read-only system knowledge;
- `/api/v1/system/...` only for controlled administration.

The path workspace is an explicit requested scope, not trusted ownership. The
API validates membership and establishes database RLS context before service
execution. Resource create/update payloads do not accept `workspace_id`.

### 4.2 Resource conventions

- UUIDs serialize as lowercase canonical strings.
- Timestamps serialize as UTC RFC 3339 strings.
- Decimal monetary/rate values serialize as strings, not JSON binary floats.
- Money uses an object with `amount`, `currency`, and declared rounding
  convention where needed.
- Units and frequencies use stable vocabulary keys.
- Resource responses distinguish `lockVersion`, `revisionNumber`, and
  `semanticVersion`; they never expose an ambiguous `version`.
- Mutable resources expose an ETag derived from `lockVersion`; updates require
  `If-Match`.
- Deletes are explicit and distinguish archive, soft delete, and purge
  request.

Example:

```json
{
  "id": "9a9a4e7e-79e1-4b0a-a6f4-cfc8df89ce04",
  "type": "concept",
  "lockVersion": 4,
  "slug": "yield-curve",
  "title": "Yield Curve",
  "lifecycleStatus": "active",
  "currentRevisionId": "a936fcea-340d-4dc5-b4cb-63a247f475b8",
  "revisionNumber": 3,
  "createdAt": "2026-08-18T22:00:00Z",
  "updatedAt": "2026-08-18T22:00:00Z"
}
```

### 4.3 Errors

Errors use `application/problem+json` following RFC 9457:

```json
{
  "type": "https://docs.jarvis.local/problems/data-provider-authentication",
  "title": "Data provider authentication failed",
  "status": 422,
  "detail": "FRED rejected the configured credential.",
  "instance": "/api/v1/workspaces/WORKSPACE_ID/data-imports/IMPORT_ID",
  "code": "data_provider.authentication_failed",
  "requestId": "REQUEST_ID",
  "action": "Review the FRED connection in Settings > Data Sources."
}
```

Error categories use stable codes:

- `authentication.*`
- `authorization.*`
- `validation.*`
- `configuration.*`
- `data_provider.*`
- `data_quality.*`
- `calculation.*`
- `model.*`
- `flow.*`
- `document.*`
- `conflict.*`
- `system.*`

Stack traces and provider secrets are never returned.

### 4.4 Pagination and filtering

Collection responses use opaque cursor pagination:

```json
{
  "items": [],
  "page": {
    "nextCursor": null,
    "hasMore": false
  }
}
```

Filters are allowlisted and typed in OpenAPI. Sort keys are allowlisted. A
cursor encodes the stable sort tuple and is integrity protected; clients do
not construct cursors.

### 4.5 Idempotency and concurrency

`Idempotency-Key` is required for retriable creation/execution endpoints such
as uploads, imports, and flow runs. The key is scoped by workspace, actor, HTTP
method, and route. Reusing a key with a different request hash returns a
conflict.

Optimistic updates use `ETag` and `If-Match`. A stale update returns
`412 Precondition Failed` with the current resource version.

### 4.6 Long-running operations

The API returns `202 Accepted`:

```json
{
  "operationId": "OPERATION_ID",
  "kind": "document_ingestion",
  "status": "pending_dispatch",
  "statusUrl": "/api/v1/workspaces/WORKSPACE_ID/operations/OPERATION_ID",
  "eventsUrl": "/api/v1/workspaces/WORKSPACE_ID/operations/OPERATION_ID/events"
}
```

Canonical run states are:

- `pending_dispatch`
- `queued`
- `running`
- `waiting_for_input`
- `retrying`
- `succeeded`
- `succeeded_with_warnings`
- `failed`
- `cancel_requested`
- `cancelled`

Polling is always supported. SSE is an optimization for state/progress events.
The canonical `operation_run`, not an SSE connection or queue row, is
authoritative. Domain-specific run resources are linked 1:1 where needed.

### 4.7 Authentication and CSRF

Browser API calls use the opaque application session cookie. Mutating requests
also require the server-issued CSRF token and a valid Origin. The OpenAPI
document describes authentication but never includes real tokens in examples.

OIDC endpoints are `/api/v1/auth/login`, `/api/v1/auth/callback`, and
`/api/v1/auth/logout`. The implementation validates an exact issuer allowlist,
signature/JWKS and algorithm, `iss`, `aud`/`azp`, time claims, nonce, one-time
server-side state/PKCE verifier, exact redirect URI, and required MFA
assurance. The owner allowlist is `(issuer, subject)`, not email.

Non-browser bearer authentication is a distinct security scheme and is not
silently enabled for the initial release.

### 4.8 Versioning and compatibility

- `/api/v1` denotes the HTTP contract major version.
- Compatible fields/endpoints can be added within v1.
- Existing meanings, required fields, and enum values are not changed
  incompatibly.
- Clients must tolerate unknown additive response fields.
- Removing or changing behavior requires deprecation, telemetry, and a new
  major contract when necessary.
- CI compares normalized OpenAPI against the previous release.

## 5. Authored flow DSL

### 5.1 Lifecycle

A logical flow has a mutable draft and immutable published versions:

```text
mutable draft -> validation -> immutable published version
immutable published version -> deprecated or withdrawn lifecycle event
```

Drafts use optimistic `lockVersion` and are not executable. Publishing creates
an immutable resource revision, flow version, and compiled plan. Deprecation or
withdrawal changes separate lifecycle metadata/events, not published DSL
content. Completed runs always reference the exact published version.

### 5.2 Example

```json
{
  "dslVersion": "1.0",
  "flowKey": "finance.yield_curve_analysis",
  "version": "1.0.0",
  "name": "Yield Curve Analysis",
  "objective": "Measure curve level, slope, and curvature from a saved snapshot.",
  "requiredPermissions": [
    "data.read",
    "flows.execute",
    "fixed_income.execute"
  ],
  "inputs": {
    "type": "object",
    "required": ["datasetSnapshotId", "maturityMap"],
    "properties": {
      "datasetSnapshotId": {
        "type": "string",
        "format": "uuid",
        "x-jarvis-resourceType": "dataset_snapshot"
      },
      "maturityMap": {
        "type": "object",
        "additionalProperties": {
          "type": "string"
        }
      }
    },
    "additionalProperties": false
  },
  "steps": [
    {
      "id": "validate",
      "handler": {
        "key": "jarvis.data.validate_snapshot",
        "version": "1.0.0"
      },
      "config": {
        "requiredColumns": ["2y", "5y", "10y", "30y"]
      }
    },
    {
      "id": "metrics",
      "handler": {
        "key": "fixed_income.yield_curve_metrics",
        "version": "1.0.0"
      },
      "config": {
        "slopePairs": [["10y", "2y"], ["30y", "5y"]],
        "curvature": ["2y", "10y", "30y"]
      }
    },
    {
      "id": "visualize",
      "handler": {
        "key": "jarvis.charts.time_series_spec",
        "version": "1.0.0"
      },
      "config": {
        "title": "Yield Curve Factors"
      }
    }
  ],
  "edges": [
    {
      "from": "$inputs.datasetSnapshotId",
      "to": "validate.datasetSnapshotId"
    },
    {
      "from": "validate.validatedSnapshotId",
      "to": "metrics.datasetSnapshotId"
    },
    {
      "from": "$inputs.maturityMap",
      "to": "metrics.maturityMap"
    },
    {
      "from": "metrics.factorSeries",
      "to": "visualize.series"
    }
  ],
  "outputSchema": {
    "type": "object",
    "required": ["factorSeries", "chartSpec", "warnings"],
    "properties": {
      "factorSeries": {
        "$ref": "jarvis://schemas/artifact-reference/1.0"
      },
      "chartSpec": {
        "$ref": "jarvis://schemas/artifact-reference/1.0"
      },
      "warnings": {
        "type": "array",
        "items": {
          "$ref": "jarvis://schemas/warning/1.0"
        }
      }
    },
    "additionalProperties": false
  },
  "outputBindings": {
    "factorSeries": "metrics.factorSeries",
    "chartSpec": "visualize.chartSpec",
    "warnings": "metrics.warnings"
  }
}
```

### 5.3 DSL rules

- Step IDs are unique within a flow version and match a restricted identifier
  pattern.
- Handler references include exact stable key and version.
- Config is validated against the handler release's JSON Schema.
- Inputs and outputs use JSON Schema 2020-12 plus documented JARVIS
  annotations.
- Large/typed outputs route through a standard artifact-reference schema
  containing artifact ID, kind, workspace, semantic/byte hashes, and media
  metadata; generic `(type, id)` references are not accepted.
- Edges connect schema-compatible output and input ports.
- A step cannot read undeclared prior state.
- Initial compiled graphs must be acyclic.
- Secret values never appear in DSL or run parameters; steps receive scoped
  secret references through capabilities.
- Conditions use a restricted JSON expression AST with an operator allowlist,
  no function calls, and no access outside declared inputs/outputs.
- All numeric literals with financial meaning declare units/conventions in the
  handler schema.

### 5.4 Publish-time compiler

Publishing fails unless the compiler verifies:

- DSL schema and supported version;
- module/handler installation and compatibility;
- flow-level and handler permissions;
- unique steps and valid acyclic edges;
- input/output schema compatibility;
- required configuration and units;
- deterministic constraints for cacheable/reproducible steps;
- timeout and retry policies;
- output mappings;
- retained execution bundle/image availability policy;
- no unresolved resources or secret literals.

The compiled plan records the compiler release and hash. Runtime executes the
compiled plan, not the mutable draft.

### 5.5 Restricted expression AST

Allowed operator families may include:

- comparisons: `eq`, `ne`, `lt`, `lte`, `gt`, `gte`;
- boolean: `and`, `or`, `not`;
- null/presence: `is_null`, `exists`;
- membership: `in`;
- scalar references to declared inputs or prior outputs.

Arithmetic and finance calculations belong in registered handlers, not
conditions. The first DSL version has no loops. Repeated operations use a
bounded, typed map handler if required.

## 6. Handler contract

### 6.1 Descriptor

Conceptual Python contract:

```python
class HandlerDescriptor:
    key: str
    version: str
    code_digest: str
    config_schema: dict
    input_schema: dict
    output_schema: dict
    required_capabilities: frozenset[str]
    deterministic: bool
    timeout_seconds: int
    max_attempts: int
    idempotency: str
```

### 6.2 Execution interface

```python
class StepHandler(Protocol):
    descriptor: HandlerDescriptor

    async def execute(
        self,
        context: StepContext,
        inputs: Mapping[str, JsonValue],
        config: Mapping[str, JsonValue],
    ) -> StepResult: ...
```

`StepContext` contains only scoped services:

- workspace, actor, flow run, step run, and attempt IDs;
- cancellation/deadline signals;
- deterministic clock/random source when required;
- authorized dataset/artifact readers and writers;
- secret handles, never plaintext serialization;
- structured logger and provenance recorder.

It does not expose an unrestricted SQLAlchemy session, filesystem, network
client, or dependency container.

Ordinary analytical handlers receive no provider client. A separately typed
import-handler context may receive one declared provider capability and must
materialize raw evidence plus a normalized dataset snapshot before downstream
analysis.

### 6.3 Result

`StepResult` contains:

- schema-validated JSON outputs;
- typed artifact references;
- warnings with stable codes and evidence;
- quality/diagnostic results;
- provenance additions;
- safe metrics.

Large values are written as artifacts and returned by reference.

### 6.4 Idempotency and retries

A step attempt key derives from:

```text
workspace + flow_run + step + handler_release + normalized_input_hash
```

Before side effects, handlers reserve or locate the idempotency record.
Repeated delivery returns the prior committed result or resumes a documented
checkpoint. A handler never assumes exactly-once delivery.

`normalized_input_hash` uses the versioned JARVIS canonical value encoding
defined by the numerical correctness policy. It is not a hash of arbitrary
language JSON serialization.

### 6.5 Error taxonomy

Handlers raise typed domain errors:

- `StepInputError`
- `StepConfigurationError`
- `StepDataQualityError`
- `StepCalculationError`
- `StepProviderError`
- `StepTimeoutError`
- `StepCancelledError`
- `StepSystemError`

Errors declare retryability and contain safe structured details. Unknown
exceptions become non-disclosing system errors and retain an internal trace ID.

### 6.6 Determinism

A deterministic handler:

- uses only declared/pinned inputs;
- uses the provided clock and random seed;
- does not make undeclared network calls;
- records engine and dependency versions;
- emits a content hash for outputs.

A non-deterministic handler must declare why and persist enough external
evidence to explain the result. AI interpretation steps are non-deterministic
and cannot produce authoritative calculations.

Published handler releases retain an execution image/bundle digest and
availability status. Workers advertise supported bundle digests/contract
ranges; dispatch will not send incompatible work. Release deployment drains
incompatible workers before contract migrations. Exact historical rerun is
available only while the retained bundle remains runnable; replay and
current-method rerun are distinct modes.

## 7. Data-provider port

### 7.1 Capabilities

Providers advertise capabilities rather than implementing FRED-specific
methods universally. The base descriptor/connection contract is small;
capability-specific protocols add their corresponding operations:

```text
series_search
series_metadata
observations
vintages
incremental_refresh
bulk_download
rate_limit_status
connection_test
```

### 7.2 Conceptual interface

```python
class DataProvider(Protocol):
    descriptor: DataProviderDescriptor

    async def test_connection(
        self, context: ProviderContext
    ) -> ConnectionTestResult:
        ...

    async def search_series(
        self, context: ProviderContext, query: SeriesSearchQuery
    ) -> Page[ProviderSeriesSummary]:
        ...

    async def get_series_metadata(
        self, context: ProviderContext, source_id: str
    ) -> ProviderSeriesMetadata:
        ...

    async def fetch_observations(
        self, context: ProviderContext, request: ObservationRequest
    ) -> ProviderFetchResult:
        ...

class VintageProvider(Protocol):
    async def list_vintages(...) -> Page[ProviderVintage]:
        ...

class IncrementalProvider(Protocol):
    async def fetch_changes(...) -> ProviderFetchResult:
        ...

class BulkDownloadProvider(Protocol):
    async def prepare_bulk_download(...) -> ProviderBulkArtifact:
        ...
```

`ProviderFetchResult` contains:

- provider request metadata;
- immutable raw response artifact;
- normalized observation stream/table;
- source metadata and units;
- provider real-time/vintage fields;
- pagination/continuation metadata;
- rate-limit metadata;
- warnings.

Provider import orchestration persists request/release metadata, continuation
state, immutable raw artifact, normalized snapshot, and quality/provenance
before completion. Analytical flows consume snapshots, never provider DTOs.

### 7.3 Provider errors

Adapters translate vendor failures into:

- authentication;
- authorization;
- not found;
- invalid request;
- rate limited with retry time;
- unavailable/retryable;
- malformed response;
- unsupported capability.

Original safe provider codes may be retained internally; credentials and raw
error bodies are redacted.

### 7.4 FRED/ALFRED requirements

The FRED adapter must:

- preserve series ID, units, frequency, seasonal adjustment, and notes;
- preserve request parameters and retrieval timestamp;
- support observation date and real-time/vintage intervals;
- retain the raw response artifact and content hash;
- distinguish missing markers from numeric zero;
- expose rate-limit/retry behavior;
- avoid labeling a snapshot backtest-safe unless vintage requirements are
  satisfied.

## 8. Supporting ports

### 8.1 `BlobStore`

Required operations:

- initiate constrained upload;
- finalize and verify size/hash/type;
- open authorized read stream;
- create short-lived signed download;
- copy/promote quarantine object;
- stat object/version;
- mark for deletion and purge;
- enumerate for controlled reconciliation.

Domain code works with blob IDs and metadata, not provider bucket URLs.

### 8.2 `SecretStore`

Required operations:

- create encrypted secret and return opaque reference;
- resolve for a scoped server-side operation;
- rotate and revoke;
- return fingerprint/configured metadata;
- audit access without recording plaintext.

Secrets are not serializable into events, jobs, API responses, or logs.

### 8.3 `JobQueue`

Required operations:

- idempotently enqueue from an outbox event;
- schedule with queue, priority, and idempotency key;
- cancel;
- retry/dead-letter;
- inspect safe queue metadata.

The creation transaction writes `operation_run(status=pending_dispatch)` and
an outbox event atomically. A dispatcher enqueues then records `queued`;
undispatched events are recoverable. Claims carry attempt generation/fencing
tokens so a stale worker cannot commit after lease loss. Cancellation is
cooperative, and current permission is revalidated before sensitive work or
side effects. Dead-letter ownership and recovery are application operations.
Queue IDs are implementation details.

The PostgreSQL queue candidate is not accepted in production until its schema
migrations, periodic stalled-job recovery, rolling compatibility, retention,
and conformance behavior are integrated into the controlled release process.

### 8.4 `DocumentExtractor`

The quarantine verifier takes an uploaded object and returns signature/MIME,
hash, encryption, page/object-limit, and malware-policy results without
publishing it. Only a verified immutable blob/version enters
`DocumentExtractor`.

The extractor outputs a versioned manifest containing pages, text/layout
artifacts, metadata candidates, warnings, and parser provenance. Verifier and
extractor run in a no-egress, separately permissioned worker pool.

### 8.5 `AIProvider`

The low-level provider port supports structured messages, tool schemas,
streaming, token/usage metadata, and model identity. The application-level AI
gateway controls authorization, retrieval, tool execution, citation
validation, prompt templates, and persistence. Provider SDK objects do not
enter domain services.

## 9. AI tool contract

An AI tool descriptor declares:

- stable key/version and owning module;
- human description;
- JSON input/output schemas;
- read/write/execute classification;
- required permission;
- confirmation and idempotency policy;
- maximum result size and redaction policy.

Every invocation:

1. authenticates the actor/session;
2. revalidates workspace membership and permission;
3. validates input;
4. calls a normal application service;
5. records resource revisions and evidence returned;
6. validates and size-limits output;
7. writes an audit/tool-call record.

Initial tools are read-only. Write or execution tools require explicit user
confirmation and are not enabled merely because a model requested them.

## 10. Domain event envelope

Internal asynchronous events use a versioned envelope:

```json
{
  "eventId": "EVENT_ID",
  "eventType": "documents.document_version_finalized.v1",
  "occurredAt": "2026-08-18T22:00:00Z",
  "workspaceId": "WORKSPACE_ID",
  "actor": {
    "kind": "user",
    "id": "USER_ID"
  },
  "correlationId": "REQUEST_OR_RUN_ID",
  "causationId": "PRIOR_EVENT_ID",
  "resource": {
    "type": "document_version",
    "id": "DOCUMENT_VERSION_ID"
  },
  "data": {
    "ingestionRequested": true
  }
}
```

Rules:

- payloads contain identifiers and safe metadata, not secrets or large data;
- consumers are idempotent by event ID;
- event schemas are committed and compatibility checked;
- an outbox writes events atomically with domain changes;
- events are integration facts, not commands disguised as facts;
- audit and provenance are not reconstructed solely from event retention.

## 11. Contract conformance

CI must include:

- manifest schema and dependency-resolution tests;
- unknown component/handler/provider/tool fail-closed tests;
- OpenAPI generation and breaking-change checks;
- generated TypeScript client drift checks;
- flow DSL schema/compiler golden cases and malicious input cases;
- handler input/output schema and idempotency tests;
- provider adapter conformance suites;
- storage/secret/job adapter contract tests;
- event schema compatibility tests;
- cross-workspace authorization tests for every public contract.

No adapter is production-ready until it passes the shared conformance suite.

## 12. Deferred contract features

These are intentionally outside the first contract version:

- arbitrary third-party executable plugins;
- cyclic flows, unbounded loops, and general-purpose scripting;
- GraphQL;
- WebSocket-only state;
- arbitrary SQL or notebook execution;
- direct model access to provider credentials;
- cross-workspace resource sharing;
- public module marketplace;
- provider-specific behavior embedded in generic flow definitions.

