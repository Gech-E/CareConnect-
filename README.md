# CareConnect

A responsive patient portal and API for clinician discovery, appointment booking,
and care management. The maintained client is a Next.js web application.

**Release status:** security and reliability hardening is implemented, but clinical
production launch is blocked by the real provider integrations and operational
validation listed in [Production readiness](docs/PRODUCTION_READINESS.md). Use
synthetic data until those gates are completed.

## Architecture

- `apps/patient-web`: Next.js, React, TypeScript; same-origin server proxy with
  HttpOnly session cookies. Browser code never receives bearer tokens.
- `services/api`: FastAPI, SQLAlchemy, PostgreSQL, Redis and S3-compatible storage.
- `services/api/app/worker.py`: Celery worker and periodic hold expiry.
- `infra/docker-compose.yml`: isolated local development infrastructure.
- `.github/workflows/ci.yml`: quality, regression, dependency and container checks.

The previously tracked clinician/admin Git links had no usable source or submodule
configuration. Those portals are not implemented in this repository. Product and
software requirements documents describe intended functionality, not a verified
release contract.

## Local setup

Requires Docker Compose, Node.js 22+ and npm. Python development uses Python 3.12
and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/Gech-E/CareConnect-.git
cd CareConnect-
docker compose -f infra/docker-compose.yml up --build -d
```

Compose waits for PostgreSQL, runs Alembic migrations, then starts the API and
workers. Services bind to loopback. API: `http://localhost:8005`; API reference:
`http://localhost:8005/docs`; MinIO console: `http://localhost:9001`.

Optional synthetic demonstration data:

```sh
docker compose -f infra/docker-compose.yml exec api python seed.py
```

The seed refuses to run outside `ENVIRONMENT=local`. It includes synthetic users
with published demonstration passwords and must never be run on a real dataset.

```sh
cd apps/patient-web
cp .env.example .env.local
npm ci
npm run dev
```

Open `http://localhost:3005`. PowerShell supports `Copy-Item` in place of `cp`.
Configure the web server's API URL using the example environment file. Requests
and sessions pass through the web server, so its upstream API must be reachable
from that server.

## Development checks

```sh
cd services/api
uv sync --frozen --extra dev --python 3.12
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Real database tests require a **dedicated** database with a name ending `_test`.
Set `DATABASE_URL` and `TEST_DATABASE_URL` to its async PostgreSQL URL, run
`uv run alembic upgrade head`, then `uv run pytest -q`. CI provisions this database
and tests token rotation/revocation and concurrent appointment exclusion. Without
`TEST_DATABASE_URL`, those integration tests are explicitly skipped.

```sh
cd apps/patient-web
npm ci
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
npm audit --omit=dev --audit-level=high
```

Commit `uv.lock` and `package-lock.json` with dependency changes. CI installs from
these locks. Format Python with `uv run ruff format .` and web files with
`npm run format`. Tests must use synthetic identities and records only.

## Deployment

See [the production runbook](docs/PRODUCTION_READINESS.md) before deploying. Build
API and web images from their respective directories. API and worker share the
same image; migrations run as a separate release command before replicas start.

- `/health/live` is process liveness; `/health/ready` checks database, Redis and
  storage, returning 503 when a dependency is unhealthy.
- Stage/production configuration rejects development secrets, debug mode,
  insecure public origins and enabled demo providers.
- Redis-backed API/auth/upload rate limits fail closed during Redis outages.
- Appointment holds use transaction locks and a PostgreSQL exclusion constraint.
- Uploaded documents remain quarantined until a trusted scanner marks them clean.
- Fake video, pharmacy, notification and FHIR operations cannot claim success in
  a production environment.

## Project documentation

- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [Production readiness and operations](docs/PRODUCTION_READINESS.md)
- [Product requirements](CareConnect_PRD_v1.0.md)
- [Software requirements](CareConnect_SRS_v1.0.md)

This repository does not currently declare an open-source license.
