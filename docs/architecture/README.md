# JARVIS Architecture

The Phase 0 baseline is:

1. [Architecture proposal](architecture-proposal.md)
2. [Data model and ERD](data-model.md)
3. [Platform contracts](platform-contracts.md)
4. [Threat model](threat-model.md)
5. [Numerical correctness policy](numerical-correctness.md)
6. [Testing strategy](testing-strategy.md)
7. [Migration and content strategy](migration-strategy.md)
8. [Deployment strategy](deployment-strategy.md)
9. [Phase 0 review and risk register](phase-0-review.md)

The governing product document is the
[master project specification](../product/master-project-specification.md).

## Decision records

- [ADR-0001: Modular monolith](decisions/0001-modular-monolith.md)
- [ADR-0002: React and Vite workstation](decisions/0002-vite-workstation.md)
- [ADR-0003: PostgreSQL primary store](decisions/0003-postgresql-primary-store.md)
- [ADR-0004: Workspace tenancy and RLS](decisions/0004-workspace-tenancy-and-rls.md)
- [ADR-0005: Trusted module manifests](decisions/0005-trusted-module-manifests.md)
- [ADR-0006: Versioned flow DSL](decisions/0006-versioned-flow-dsl.md)
- [ADR-0007: Object storage and snapshots](decisions/0007-object-storage-and-snapshots.md)
- [ADR-0008: OIDC and server sessions](decisions/0008-oidc-and-server-sessions.md)
- [ADR-0009: PostgreSQL-backed jobs](decisions/0009-postgresql-backed-jobs.md)
- [ADR-0010: OpenAPI contract](decisions/0010-openapi-contract.md)
- [ADR-0011: Embedded PostgreSQL tests](decisions/0011-embedded-postgresql-tests.md)

Phase 0 is documentation only. The first application implementation must follow
the sequence and gates in the proposal and Phase 0 review.

