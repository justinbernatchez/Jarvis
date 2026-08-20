# ADR-0001: Use a Modular Monolith

- Status: Accepted
- Date: 2026-08-18

## Context

JARVIS spans identity, platform configuration, knowledge, documents, data,
flows, research, analytics, search, and AI. These domains need strong
boundaries, but the initial product has one owner, one development team, and no
measured requirement for independent service scaling.

Many core operations require relational consistency. Examples include
publishing a flow version, pinning an analysis to dataset snapshots, and
writing audit and outbox records with the corresponding state change.

## Decision

Build one Python modular monolith with:

- bounded contexts and explicit public application facades;
- one PostgreSQL database with schema/table ownership by context;
- separate API and worker process entry points importing the same packages;
- typed events and a transactional outbox for asynchronous boundaries;
- architecture tests that reject imports of another context's ORM models or
  repositories.

The web client is a separate deployable static application, but all business
logic remains behind the FastAPI API.

## Consequences

Benefits:

- transactions and referential integrity remain straightforward;
- local development and deployment require fewer moving parts;
- domain boundaries can be tested before network boundaries are introduced;
- background work can scale separately through worker replicas;
- selected contexts can be extracted later through existing ports/events.

Costs:

- module discipline must be enforced in code review and tests;
- one database can become a coordination point;
- a poorly factored monolith could still become tightly coupled.

## Extraction criteria

A context becomes a separate service only when at least one condition is
demonstrated:

- it requires materially different scaling or hardware;
- its failures must be isolated from the API;
- it has an independent release or security boundary;
- database contention cannot be solved with normal PostgreSQL techniques;
- a dedicated owning team exists.

Document processing, heavy analytics, search, provider ingestion, and AI
orchestration are the first likely candidates. Microservices are not a Phase 1
deliverable.

