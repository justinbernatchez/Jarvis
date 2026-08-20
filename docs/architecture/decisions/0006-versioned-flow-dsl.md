# ADR-0006: Use a Versioned, Compiled Flow DSL

- Status: Accepted
- Date: 2026-08-18

## Context

Research workflows must be reusable and user-configurable rather than
implemented as one React page per analysis. They also execute calculations,
transform data, and create durable research records, so arbitrary workflow
code stored in the database would be unsafe and irreproducible.

## Decision

Represent work-in-progress as a mutable flow draft protected by optimistic
locking. A draft is not executable. Publishing snapshots it into an immutable,
versioned, schema-validated flow document and compiles validated steps and
edges that reference pinned, registered handler releases.

Initial flows are directed acyclic graphs. Conditions use a restricted,
type-checked expression language over declared step outputs. The DSL cannot
contain arbitrary Python, JavaScript, SQL, shell, imports, or class names.

Every handler release declares:

- stable key, semantic version, and code digest;
- configuration, input, and output schemas;
- required permissions and capabilities;
- deterministic classification;
- timeout, retry, cancellation, and idempotency policy.

Every run records the exact flow version, handler digests, dataset snapshots,
parameters, assumptions, transformations, random seed, outputs, warnings, and
artifacts.

A handler digest proves what ran but not that the implementation remains
available forever. Exact rerun requires a retained execution image/bundle by
digest and compatibility checks. Otherwise JARVIS may replay stored evidence
or rerun a current compatible method and must label the reproducibility level.

## Consequences

Benefits:

- one execution model supports many finance and future-domain workflows;
- flows can be validated before execution;
- completed analyses remain reproducible when definitions change;
- handlers are testable and reusable outside the UI;
- user-authored flows compose reviewed capabilities without executing code.

Costs:

- DSL and compiler design require careful versioning;
- loops and complex interactive branching are deferred;
- handler evolution needs compatibility rules and migrations;
- exact reruns require retention and vulnerability management for historical
  execution images;
- at-least-once job execution requires idempotent steps.

The abstraction is accepted only after Yield Curve Analysis, Macro Time-Series,
and Equity DCF all run through the same engine without flow-specific engine
branches.

