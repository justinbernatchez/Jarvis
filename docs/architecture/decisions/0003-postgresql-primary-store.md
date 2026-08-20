# ADR-0003: Use PostgreSQL as the Primary Structured Store

- Status: Accepted
- Date: 2026-08-18

## Context

JARVIS requires relational constraints, multi-workspace isolation, versioned
knowledge, graph-like relationships, workflow state, full-text search, audit
records, and reproducible lineage. Introducing separate document, graph,
search, vector, and workflow databases at the start would increase consistency
and operational risk.

## Decision

Use the latest patched PostgreSQL 18 release as the primary structured source
of truth.

Use:

- relational tables and foreign keys for identity, ownership, state, lineage,
  versions, and frequently queried attributes;
- PostgreSQL schemas to make bounded-context ownership visible;
- row-level security as defense in depth for private workspace data;
- `tsvector`, GIN indexes, and `pg_trgm` for initial search;
- JSONB only for schema-validated cohesive documents;
- Alembic for one ordered migration history.

Do not add a graph database, separate search engine, or vector database during
the architecture-validation MVP. Add `pgvector` only after a measured semantic
search requirement.

## Consequences

Benefits:

- strong transactions and referential integrity;
- fewer consistency boundaries and less infrastructure;
- mature indexing, full-text search, JSONB, and row security;
- one backup and recovery path for structured state.

Costs:

- very large observations and binary artifacts do not belong in ordinary
  relational rows;
- search projections require deliberate indexing and maintenance;
- queue/search workloads must be monitored for database contention.

Large immutable PDFs, raw payloads, Parquet datasets, and analysis artifacts
are stored in S3-compatible object storage. PostgreSQL retains their metadata,
hashes, ownership, and lineage.

