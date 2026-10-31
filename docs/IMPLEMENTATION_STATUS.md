# Implementation status (2026-10-31)

## Delivered on the feature branch

- Expo patient app with branded home, clinician directory, specialty selection, profile, availability, appointment booking, basic account screens and appointments.
- API client using existing endpoint contracts and bearer authorization, URL encoding, typed response models, normalized error states.
- Native access-token storage through Expo SecureStore; web token is intentionally in memory only.
- Authentication hardening: self-service patient registration, access/refresh token type checking, issuer validation, expiry checks, DB session validation, expiry timestamps.
- Root README, ignore rules, development environment example.

## Major gaps and security gates

1. **Do not deploy with actual PHI.** Finish threat modeling, external security review, encryption/key management, activity audit verification and legal review.
2. Previously committed `services/api/.env` is removed on this branch. Review repository history; rotate any secrets that were real, and if required remove them from git history using an approved process.
3. Registration currently creates unverified accounts. Protected health data must remain blocked until verified identity and documented telehealth consent are implemented.
4. Token refresh needs rotation/reuse detection, audit, and security tests.
5. Rate limiting middleware in existing code is not yet enforcing a production policy.
6. Appointment overlap enforcement requires DB-level concurrency constraint/locking; existing logic checks overlap but is vulnerable to simultaneous requests.
7. Reconcile user and practitioner IDs in clinician endpoints and ensure all record/message download paths enforce contextual authorization.
8. Verify migrations and seed script against the API; fix response contract drift (some Pydantic schemas and response objects disagree).
9. Clinician/admin directories in the base tree are gitlinks, not regular source folders; verify their target repositories before integrating.
10. Run npm typecheck, Ruff, mypy, unit, API integration, and end-to-end device checks in a real CI environment. No build/test pass is claimed here.

## Visual direction

- Warm off-white surfaces, deep slate text, accessible teal CTAs, gentle elevation through strokes and rounded corners.
- Patient-focused task hierarchy, no fake doctor photos, no fabricated clinician credentials.
- States: loading, empty, network error, guest account, session sign-out, slot selection and booking failure.
- Next: clinician/admin portals, records/messaging, onboarding, comprehensive accessibility and localization.
