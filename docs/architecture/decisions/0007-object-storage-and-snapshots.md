# ADR-0007: Use Object Storage and Immutable Snapshots

- Status: Accepted
- Date: 2026-08-18

## Context

JARVIS must preserve original papers, provider responses, exact analysis
datasets, generated reports, and model artifacts. Large binary and columnar
payloads are a poor fit for normal relational rows, while object storage alone
cannot provide the metadata, lineage, and authorization required by the
application.

## Decision

Use S3-compatible private object storage behind a `BlobStore` port.

Store in object storage:

- original PDFs and document derivatives;
- immutable raw provider responses;
- Parquet/Arrow dataset snapshots;
- large charts, reports, model artifacts, and execution logs.

Store in PostgreSQL:

- ownership and access scope;
- content type, size, checksum, object key, and storage version;
- logical resource and immutable revision/snapshot identity;
- provenance, lineage, retention state, and creation metadata.

Use content hashes for deduplication and integrity, but never infer
authorization from a hash. Object keys are workspace scoped. Access uses
short-lived signed URLs after authorization.

Deduplication is limited to the same workspace/security domain by default.
Cross-workspace physical deduplication is not exposed through timing,
existence, reference-count, or authorization behavior and requires a separate
privacy review.

Raw, normalized, and analysis-ready datasets are separate immutable snapshots
connected by versioned transformation runs. Reprocessing creates a new
artifact; it does not replace historical evidence.

## Consequences

Benefits:

- originals and exact analytical inputs remain reproducible;
- PostgreSQL stays focused on structured metadata and interactive queries;
- storage providers can change without changing domain code;
- large payload delivery can bypass API memory through signed URLs.

Costs:

- database and object writes require compensating cleanup or an outbox-driven
  finalize process;
- lifecycle and orphan detection must be implemented;
- backups must cover both stores consistently;
- object versions and KMS keys must be retained for at least the PostgreSQL
  point-in-time recovery horizon;
- local development needs an S3-compatible emulator or filesystem adapter.

