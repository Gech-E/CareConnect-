# CareConnect implementation status

**Scope:** Browser-based web application only. No native iOS/Android client is maintained.

## Current implementation

- Responsive patient portal in `apps/patient-web`, built with Next.js, React, TypeScript and CSS.
- Home, clinician directory, search/filter, clinician details, slot lookup, sign-in/registration, booking and appointment list screens.
- Existing FastAPI services for authentication, discovery, appointment management, messaging, records, prescriptions, clinician/admin workflows and integrations.
- Browser client uses short-lived in-memory bearer tokens to avoid writing tokens to localStorage.
- Backend local stack: PostgreSQL, Redis, MinIO and Celery, configured via Docker Compose.
- Expo patient mobile application source was removed from the working tree.

## Not complete / verification required

1. **Do not use with real patients or real PHI.** Clinical/legal/privacy security review is outstanding.
2. Run `npm install && npm run typecheck && npm run build` in `apps/patient-web`. These checks have not been executed by GitHub connector operations.
3. Execute API integration and end-to-end browser tests against the local database and Redis.
4. Verify email/identity verification, consent, clinician licensing and service-area restrictions.
5. Rework browser login for production using a carefully reviewed BFF and secure HttpOnly cookies.
6. Enforce database-level appointment conflict protection and idempotency under concurrency.
7. Complete clinician and admin web apps: current directories are Git links whose source hasn't been verified here.
8. Finish messaging, visits, documents, prescriptions and video UI.
9. Add CI, accessibility tests, dependency scanning, threat model, rate limits, robust audit events and security review.

## Visual system

- Off-white background, deep slate text, muted teal accent and soft mint surfaces.
- Rounded cards, clear primary actions, responsive grids and simple top navigation.
- Error, loading, empty-list and authentication-required states.
- No fabricated clinician records, credentials, reviews or slots in the app; lists are fetched from the API.

## Important note

Existing PRD/SRS files still specify React Native/Expo as the planned patient client. Those documents require a formal web-first revision before claiming complete alignment.
