# Google Antigravity build prompt — CareConnect Telehealth

Create a new Antigravity Project using this repository folder, then attach:

- `CareConnect_PRD_v1.0.md`
- `CareConnect_SRS_v1.0.md`
- the supplied Figma screenshots

Paste the following prompt:

---

Build **CareConnect Telehealth** from the attached PRD, SRS, and screenshots.

## Required architecture

Create a production-quality monorepo:

- `apps/patient-mobile`: React Native + Expo + TypeScript
- `apps/clinician-web`: Next.js + TypeScript
- `apps/admin-web`: Next.js + TypeScript
- `services/api`: FastAPI + Pydantic + SQLAlchemy + Alembic
- `services/worker`: Redis-backed background jobs
- `packages/contracts`: generated typed API clients
- `packages/ui-tokens`: shared design tokens
- `infra`: Docker Compose for local development and Terraform-ready production modules

Use PostgreSQL, Redis, encrypted S3-compatible object storage, OpenAPI, and an OIDC identity-provider abstraction. Use adapter interfaces and local mocks for video, FHIR/EHR, pharmacy, email/SMS/push, and payments. Never require real vendor credentials to run locally.

## MVP features

Implement:

1. patient registration, sign-in, consent, emergency disclaimer, profile, insurance, and session management;
2. specialty/concern selection, clinician search, filters, recommendations, profile, reviews, and eligibility;
3. availability, slot hold, idempotent booking, confirmation, upcoming/past appointments, reschedule, and cancel;
4. waiting room, camera/microphone/network checks, secure document upload, mock video call, weak-network state, reconnect, audio-only fallback, and visit completion;
5. secure messaging with attachments and generic push previews;
6. records list/detail/download with provenance;
7. prescription detail and non-controlled fulfillment request;
8. clinician portal for profile, availability, appointment queue, video visit, messaging, and encounter documents;
9. admin portal for support lookup, clinician status, audit search, configuration, and integration health.

Match the screenshots closely, but correct the PRD design issues: use one brand name, distinct patient/clinician identities, dynamic dates, no truncated headers, consistent appointment data, accessible contrast, and no unverified “HIPAA compliant” claim.

## Security and quality rules

- Synthetic data only. Do not place real PHI, secrets, or credentials in code, logs, fixtures, screenshots, analytics, URLs, or notifications.
- Enforce server-side RBAC/context authorization and deny by default.
- Use short-lived tokens, secure mobile storage, MFA-ready workforce auth, audit events, rate limits, file validation, malware-scan interface, signed downloads, centralized log redaction, and encryption-ready configuration.
- Follow WCAG 2.2 AA, OWASP ASVS Level 2, and OWASP MASVS.
- Exclude controlled-substance prescribing, EPCS, autonomous diagnosis, and video recording.
- Add loading, empty, offline, permission-denied, conflict, expired-session, and third-party-failure states.
- Use latest stable dependencies, strict TypeScript, Python type checking, linting, formatting, and no deprecated packages.
- Add unit, integration, contract, authorization, accessibility, and E2E tests. Critical domain modules must target at least 80% branch coverage.
- Generate OpenAPI docs, database migrations, seed data, `.env.example`, ADRs, threat model, README, runbook, and CI workflow.
- Local startup must work with documented commands and mocked integrations.

## Execution order

1. Inspect all attached files and create an implementation plan, architecture diagram, domain model, API map, backlog, and risks.
2. Scaffold the monorepo and local Docker environment.
3. Build the vertical slice: discovery → clinician profile → slot hold → booking → reminder → waiting room → mock call → completion.
4. Add messaging, records, prescriptions, profile/insurance, clinician portal, and admin portal.
5. Run lint, type checks, tests, accessibility checks, and browser/mobile smoke tests.
6. Fix failures before proceeding. Do not mark a feature complete without linked tests and SRS requirement IDs.
7. Produce a final verification report listing implemented requirements, commands run, test results, known limitations, and next production steps.

Use small, reviewable commits. Do not silently weaken a requirement. When a real vendor or legal decision is required, implement a secure interface and mock, document the decision, and continue with the rest of the build.

---