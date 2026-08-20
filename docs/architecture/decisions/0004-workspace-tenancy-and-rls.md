# ADR-0004: Use Workspace Ownership and Row-Level Security

- Status: Accepted
- Date: 2026-08-18

## Context

The first release is personal, but the product specification requires a future
multi-user architecture and explicit separation between shared system
knowledge and private user data. Direct `user_id` ownership makes
collaboration, team projects, and ownership transfer expensive to add later.

## Decision

Model a tenant as a workspace:

- a user may belong to multiple workspaces through memberships;
- the initial user receives one personal workspace and Owner membership;
- every private root record has non-null `workspace_id`;
- `created_by_user_id` and `updated_by_user_id` are attribution fields only;
- curated shared content lives in a read-only system resource namespace;
- private content lives in a workspace resource namespace.

Enforce isolation at multiple layers:

- derive workspace context from authenticated membership;
- never accept ownership from a request body;
- use composite workspace-aware foreign keys where private rows reference one
  another;
- apply PostgreSQL row-level security to private operational tables;
- set user/workspace context with `SET LOCAL` inside every transaction;
- ensure API and worker roles do not own tables or have `BYPASSRLS`;
- scope object keys, cache keys, job payloads, and search projections by
  workspace;
- maintain adversarial cross-workspace integration tests.

## Consequences

Benefits:

- personal, team, and future collaborative usage share one ownership model;
- database policy protects against missing application filters;
- ownership transfer does not require rewriting every resource;
- shared system knowledge remains distinguishable from private overlays.

Costs:

- transactions require correctly established security context;
- RLS and connection-pool behavior need dedicated tests;
- composite keys and explicit namespace rules add schema complexity;
- operational tooling must use controlled elevated roles.

RLS is defense in depth, not a substitute for application authorization.

