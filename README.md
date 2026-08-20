# JARVIS

Personal Finance Intelligence & Research Operating System.

JARVIS is being designed as a modular, database-driven platform for finance
knowledge, research, data, reproducible analysis, and an evidence-backed AI
assistant.

Phase 0 is approved. The Phase 1 platform foundation is implemented and
stopped at its review gate; finance functionality has not started.

- [Master project specification](docs/product/master-project-specification.md)
- [Architecture documentation](docs/architecture/README.md)
- [Phase 0 proposal](docs/architecture/architecture-proposal.md)
- [Phase 0 review and risk register](docs/architecture/phase-0-review.md)
- [Phase 1 implementation report](docs/phase-1/phase-1-foundation-report.md)

## Foundation development

Requirements:

- Python 3.13 and uv;
- Node.js 24 and pnpm 11;
- Docker for the PostgreSQL 18.6 development profile (tests can use embedded
  PostgreSQL when Docker is unavailable).

```text
uv sync --all-packages
pnpm install
docker compose -f infrastructure/docker/compose.yaml up -d
uv run --all-packages alembic upgrade head
uv run --all-packages jarvis-bootstrap
pnpm dev:api
pnpm dev:web
```

Configure `.env` from [.env.example](.env.example), including a conformant OIDC
provider, before interactive sign-in.

Run the complete local gate:

```text
pnpm check
```
