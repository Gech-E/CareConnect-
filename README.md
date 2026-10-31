# CareConnect

CareConnect is a **telehealth development prototype** for clinician discovery, appointments, secure communications, and care coordination. The repository includes a FastAPI backend and a new React Native patient experience.

> **Not for real patient data or clinical production.** Authentication, consent, practitioner licensing checks, clinical safety, secure integrations, monitoring, and compliance controls must be independently verified before deployment.

## Project structure

- `apps/patient-mobile/`: Expo + React Native + TypeScript patient app
- `apps/clinician-web/`, `apps/admin-web/`: existing gitlink entries; source availability must be resolved independently
- `services/api/`: FastAPI, SQLAlchemy, Alembic
- `services/worker/`: background job service
- `infra/`: local PostgreSQL, Redis, MinIO, email catcher, API and workers
- `CareConnect_PRD_v1.0.md` and `CareConnect_SRS_v1.0.md`: requirements and acceptance criteria

## Local development

1. Install Docker Engine/Compose, Node.js, and a recent Python 3 environment.
2. `cp services/api/.env.example services/api/.env` and replace example keys.
3. `docker compose -f infra/docker-compose.yml up --build -d`
4. `docker compose -f infra/docker-compose.yml exec api alembic upgrade head`
5. Use **synthetic** fixture data only. The existing `services/api/seed.py` must be checked before running.
6. `cd apps/patient-mobile && npm install && npm start`
7. Configure `EXPO_PUBLIC_API_URL` using `apps/patient-mobile/.env.example`. Android emulator: `http://10.0.2.2:8005/api/v1`; iOS simulator: `http://localhost:8005/api/v1`; physical phones need a LAN-reachable host.
8. Run `npm run typecheck` from `apps/patient-mobile`.

## Security rules

- Never commit credentials, personal health information, or patient records.
- Dev credential defaults in Docker are strictly for isolated local development.
- API self-registration is patient-only; staff access must be provisioned through approved internal administration.
- Access tokens are not accepted as refresh tokens; revoked/expired sessions cannot authorize requests.
- Use secure TLS, network isolation, credential rotation, patient verification, audit review, rate limits and comprehensive authorization before external exposure.

## Remaining work

This first implementation slice does **not** establish production readiness. Key work includes end-to-end tests, device verification, practitioner licensing/service area validation, onboarding consent, full patient profile, medical records, secure messages, clinician/admin app source integration, robust concurrency protection for slot holds, telehealth vendor adapters, accessibility verification, deployment controls and independent clinical/legal review. See `docs/IMPLEMENTATION_STATUS.md`.
