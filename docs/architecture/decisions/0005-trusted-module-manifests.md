# ADR-0005: Separate Trusted Module Code from Database Configuration

- Status: Accepted
- Date: 2026-08-18

## Context

JARVIS must be configuration-driven and allow modules, navigation, content,
flows, providers, and AI tools to evolve without hard-coded finance pages.
However, treating database configuration as arbitrary executable code would
create a remote-code-execution and maintainability problem.

## Decision

Use a two-level module registry:

1. Versioned code manifests declare trusted executable capabilities,
   dependencies, permissions, configuration schemas, route/component keys,
   provider adapters, flow handlers, and AI tools.
2. Database records install a module release into a workspace and configure
   enablement, labels, ordering, navigation, and content.

Database configuration can reference only allowlisted keys declared by an
installed module release. It cannot contain import paths, source code, SQL,
shell commands, or dynamically loaded class names.

The frontend maps component keys to statically shipped lazy imports. The
backend maps handler/provider/tool keys to registered implementations.

## Consequences

Benefits:

- navigation and content remain database/configuration driven;
- executable behavior remains reviewable, testable, and deployable;
- module compatibility and dependencies can be checked before installation;
- the contract can later support packaged plugins without an unsafe runtime.

Costs:

- a new executable capability still requires a code release;
- manifest compatibility and upgrade behavior require versioning;
- not every future third-party plugin can run in-process safely.

Untrusted third-party code, if ever supported, requires a separate isolation
model and is not part of the MVP.

