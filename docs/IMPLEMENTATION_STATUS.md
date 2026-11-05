# Implementation status

The maintained scope is a responsive browser application. Native mobile apps and
clinician/admin portals are not maintained here.

## Implemented

- Patient discovery, availability, authentication, booking and appointment UI.
- Server-side web proxy, HttpOnly sessions and same-origin mutation checks.
- Patient-only public registration, Argon2id password hashing with legacy bcrypt
  migration, validated JWTs, atomic refresh rotation and server-side revocation.
- Explicit patient/clinician authorization for appointment, encounter, video,
  prescription, record and document access.
- Transactional reservations and PostgreSQL protection against overlapping active
  appointments; timezone-aware slot generation and automatic hold expiry.
- Production settings validation, Redis rate limiting, bounded readiness checks,
  sanitized error responses and protected document download links.
- Reproducible dependencies, formatter/lint gates, regression tests, CI, container
  builds, isolated local Compose infrastructure and deployment documentation.

## Release limitations

- Identity/email verification and clinician credential/licensing verification need
  real operational providers and acceptance testing.
- Video, pharmacy delivery, email/SMS/push and FHIR adapters remain incomplete.
  Demo functionality is unavailable when demo providers are disabled.
- Document scanning must be integrated with a trusted scanner before downloads
  can be enabled for uploaded files. Client upload completion is not scan approval.
- Clinician/admin dashboards and patient messaging/records/prescription screens
  are incomplete.
- A full clinical launch requires the operational gates and independent review
  in [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md).

Passing automated tests is evidence for the tested behavior, not a claim of
clinical certification, regulatory compliance or complete product scope.
