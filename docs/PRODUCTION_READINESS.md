# Production readiness and operations

## Release decision

This hardening pass fixes concrete security, data-integrity and build problems.
It is not approval to process real patient data. The remaining launch gates below
must be completed and verified in the intended hosting environment.

## Fixed in this review

| Area | Original problem | Control added |
| --- | --- | --- |
| Authentication | Refresh replay, weak configuration defaults, brittle bcrypt setup | Atomic rotation, server-side revocation, deployment validation, Argon2id |
| Browser sessions | Tokens in client memory; session lost on reload | Same-origin server proxy and HttpOnly cookies |
| Access control | Missing or incorrect ownership checks in clinical operations | Shared patient/clinician relationship checks and role restrictions |
| Appointments | Concurrent holds could overlap; stale holds never expired | Practitioner locks, GiST exclusion constraint and periodic expiry |
| Documents | Client completion could imply a clean upload | Server metadata checks, quarantine and scanner-gated downloads |
| Integrations | Placeholder operations returned success | Explicit simulation in development and failure outside demo mode |
| Operations | Broken Docker install order, duplicated worker, false health success | Locked multistage image, single worker entrypoint, liveness/readiness split |
| Quality | No lockfiles or CI, generated commit artifacts | Locked dependencies, format/lint/test/build/audit gates and artifact removal |

## Required before clinical launch

1. Implement and acceptance-test email/identity verification, clinician credential
   approval, service-area/eligibility policy, versioned consent, and the workflows
   for account recovery and account closure.
2. Configure real video, pharmacy, email/SMS/push and FHIR adapters, with delivery
   acknowledgements, retry/idempotency behavior and monitoring. Local simulations
   are not integrations. Production deliberately rejects enabled demo providers.
3. Add a trusted malware-scanning pipeline for uploaded objects. Finalization by
   the uploading client does not constitute scan approval. Validate content type,
   scan result and content hash before marking a document available.
4. Complete the missing clinician/admin and patient clinical screens, then run
   end-to-end patient and clinician acceptance tests on a staged deployment.
5. Establish data retention/deletion policy, restricted audit access, incident
   response, monitoring ownership and independent privacy/security review. This
   repository does not establish regulatory compliance.
6. Verify backups and restore with a measured recovery target; exercise failover,
   load, race conditions and dependency outages in staging. Review dependency and
   container advisories at release time.

## Configuration

Use a secret manager to inject environment variables. Never copy the local Compose
credentials into a public deployment. Set `ENVIRONMENT=staging` or `production`,
`DEBUG=false`, `DATABASE_ECHO=false` and `ENABLE_DEMO_PROVIDERS=false`.

Generate an independent high-entropy `JWT_SECRET_KEY` of at least 48 bytes. Use
HTTPS for `OIDC_ISSUER_URL`, approved exact `ALLOWED_ORIGINS`, and custom storage
endpoints. Use a private, authenticated PostgreSQL/Redis deployment and encrypted
transport. Configure `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`,
`CELERY_RESULT_BACKEND`, `S3_BUCKET_NAME`, `S3_REGION` and storage credentials or
workload identity. Production configuration rejects known local defaults.

For the web app, follow `apps/patient-web/.env.example`. Set the upstream API URL
on the server and serve the public application over HTTPS. Configure a trusted
reverse proxy; never blindly trust user-provided forwarding headers. Rate limits
use the API's trusted ASGI peer, so proxy topology and per-user limits must be
validated under expected traffic before launch.

## Release procedure

1. Run all CI jobs on the exact release revision. Build immutable API/web images.
2. Back up PostgreSQL and confirm a recent restore drill before schema changes.
3. Inspect existing bookings for overlaps and invalid start/end intervals. The
   new constraint migration intentionally fails on existing conflicts; resolve
   those through an audited operational process, never automatic deletion.
4. Run `alembic upgrade head` once using a migration role allowed to install
   `btree_gist`. The runtime role should not have schema-changing privileges.
5. Start API and worker replicas with the same image. Start exactly one Celery
   beat scheduler. Use a writable temporary schedule path for beat.
6. Check `/health/live`, then `/health/ready` (database, Redis, storage). The latter
   returns HTTP 503 on dependency failure; configure load balancing accordingly.
7. Verify login, refresh, logout, discovery, booking/cancellation and authorization
   boundaries from the deployed web origin. Confirm no token or sensitive response
   is cached, and inspect logs for unintended sensitive data.

## Rollback and failure behavior

Keep the previous immutable images and database backup. Review schema compatibility
before rolling back application images. Avoid blindly running Alembic downgrade:
removing the booking exclusion constraint removes a data-integrity protection.

Redis loss causes rate-limited API requests to return 503 instead of silently
turning off protection. Storage loss makes readiness fail and document operations
unavailable. Investigate dependency health before increasing retry rates. API
liveness remains independent so transient dependency outages do not create a
restart loop.

Hold expiry runs every minute, processing up to 500 locked rows per task. Duplicate
jobs safely skip rows locked by another worker. Monitor backlog growth and worker
failures. Demo delivery/FHIR tasks return `simulated`, never `sent` or `synced`.

## Validation evidence

Verified locally on 5 November 2026:

- 57 API tests passed against PostgreSQL 16.15, including refresh replay/revocation,
  simultaneous booking exclusion and idempotent expiry of appointment holds.
- 14 web tests, lint, formatting, TypeScript and the production build passed.
- Locked API runtime dependency audit and production npm audit found no known
  vulnerabilities. A development-only ESLint/minimatch advisory remains.
- HTTP smoke checks passed for registration, login, cookies, logout, discovery,
  booking retries, appointment listing, cross-patient denial and cancellation.

Docker is unavailable on this workstation; container checks are configured in CI.
Browser visual inspection and the local MinIO source-build launch were blocked by
an automatic approval-review usage limit. The local demo supports authentication
and booking; document storage remains unavailable until MinIO is started.

Real PostgreSQL tests use `TEST_DATABASE_URL` and enforce a `_test` database suffix;
without it they are skipped. CI starts the development containers and checks
readiness and synthetic seeding. These checks do not replace staging load tests or
clinical workflow acceptance. Browser sessions expire with the access token and
require login again; refresh tokens are not stored by the web proxy. API refresh
rotation immediately invalidates the previous session token.

## History cleanup

The previous `main` contained 3,687 reachable commits, including generated history
and a previous consolidation that was merged back into the old graph. The cleanup
preserves the code snapshot and this hardening work in a short replacement history.
A verified local Git bundle preserves the previous references under the ignored
`backups/` directory. Do not merge an old branch back into the replacement history;
that would reintroduce the removed commits. Existing clones should be freshly
cloned, or have intentional uncommitted work saved before resetting to the new main.

## Technical references

- [FastAPI dependency lifetime](https://fastapi.tiangolo.com/advanced/advanced-dependencies/):
  database transactions close before the response is sent using function scope.
- [PostgreSQL range exclusion constraints](https://www.postgresql.org/docs/16/rangetypes.html):
  active appointment intervals cannot overlap for a practitioner.
