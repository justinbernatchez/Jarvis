# JARVIS Workstation

React/TypeScript/Vite application shell for the Phase 1 platform foundation.

The shell:

- authenticates through the FastAPI server session;
- selects a workspace;
- loads configuration-driven navigation;
- resolves component keys only through the static trusted registry;
- intentionally contains no finance dashboards or workflows.

Run from the repository root:

```text
pnpm dev:web
```

