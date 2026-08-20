# ADR-0002: Use React and Vite for the Workstation

- Status: Accepted
- Date: 2026-08-18

## Context

The primary interface is an authenticated, desktop-first research workstation
with dense tables, charts, command navigation, PDF reading, and multi-panel
interaction. Public SEO pages and server-rendered content are not part of the
initial application.

The backend must remain the authoritative API for future web, desktop, mobile,
agent, and automation clients.

## Decision

Use a strict TypeScript React single-page application built with Vite.
Use TanStack Router and Query for routing and server state. Produce static
assets for production and route `/api` to FastAPI under the same origin.

Do not use Next.js for the authenticated workstation.

## Consequences

Benefits:

- one business-logic server boundary instead of FastAPI plus a Node backend;
- no React Server Component, Server Action, or framework cache semantics in
  application features;
- simple static deployment and preview artifacts;
- straightforward reuse of the API by future clients;
- a good fit for long-lived client interaction state.

Costs:

- the host must provide an SPA fallback to `index.html`;
- initial HTML is not server-rendered;
- secure browser authentication must be handled by the API/session design;
- a separate application is required if public SEO content becomes important.

## Revisit criteria

Reconsider only if JARVIS gains substantial public, indexable content or needs
server rendering for a measured user-experience requirement. A public website
may use a different framework without moving workstation business logic out of
FastAPI.

