# ADR-0010: Use OpenAPI as the Cross-Language Contract

- Status: Accepted
- Date: 2026-08-18

## Context

The web client is TypeScript and the authoritative backend is Python. Manually
duplicating request/response types would allow contracts to drift. Sharing
runtime domain packages across the two languages is not practical.

## Decision

FastAPI/Pydantic DTOs generate the canonical OpenAPI 3.1 document.

- Commit the normalized OpenAPI artifact.
- Generate the TypeScript client and models into `packages/ts/api-client`.
- Never expose SQLAlchemy models directly.
- Check generated-code drift in CI.
- Compare the contract against the previous release and require explicit
  approval for breaking changes.
- Keep event schemas under `contracts/events` with the same versioning
  discipline.

## Consequences

Benefits:

- one API schema source;
- typed clients for web and future consumers;
- reviewable contract changes;
- interactive documentation and conformance testing.

Costs:

- code generation becomes a build prerequisite;
- generator version changes can produce noisy diffs;
- some domain invariants still require prose and behavioral tests;
- generated clients must not become a second hand-edited source.

