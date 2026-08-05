---
title: "CareConnect Telehealth Platform"
subtitle: "Software Requirements Specification (SRS)"
author: "Prepared for Getachew Ekubay"
date: "5 August 2026"
version: "1.0"
---

# Document control

| Field | Value |
|---|---|
| System | CareConnect Telehealth Platform |
| Document | Software Requirements Specification |
| Version | 1.0 |
| Status | Build-ready baseline |
| Requirement language | “Shall” indicates a mandatory requirement |
| Market assumption | United States |
| Compliance posture | HIPAA-ready architecture; compliance requires organizational controls and validation |
| Data policy | Synthetic data only until production governance is approved |

# 1. Purpose and scope

This SRS defines the functional, interface, data, security, quality, deployment, and verification requirements for CareConnect Telehealth.

The system comprises:

- a cross-platform patient mobile application;
- a clinician web portal;
- an operations/admin web portal;
- a FastAPI application service;
- PostgreSQL, Redis, encrypted object storage, and background workers;
- vendor adapters for identity, video, notifications, FHIR/EHR, laboratory records, pharmacy fulfillment, and optional payments;
- CI/CD, infrastructure as code, monitoring, audit logging, backup, and recovery.

This SRS does not certify regulatory compliance or clinical safety. It defines controls intended to support a compliant implementation.

# 2. System context

## 2.1 Logical architecture

```text
Patient Mobile App         Clinician Web           Admin Web
        |                       |                       |
        +---------------- HTTPS / OIDC ----------------+
                                |
                         API Gateway / WAF
                                |
                         FastAPI Application
     +------------------+-------+-------+------------------+
     |                  |               |                  |
 PostgreSQL          Redis/Jobs      Object Store      Audit Store
     |                  |               |                  |
     +-------- Integration Adapter Layer ------------------+
                |          |          |         |
              Video      FHIR/EHR   Messaging  Pharmacy/Lab
```

## 2.2 Recommended repository structure

```text
careconnect/
  apps/
    patient-mobile/        # React Native + Expo + TypeScript
    clinician-web/         # Next.js + TypeScript
    admin-web/             # Next.js + TypeScript
  services/
    api/                   # FastAPI, SQLAlchemy, Alembic
    worker/                # background jobs
  packages/
    contracts/             # OpenAPI-generated clients and shared schemas
    ui-tokens/             # design tokens
    config/                # lint, formatting, tsconfig
  infra/
    terraform/
    docker/
  docs/
    prd/
    srs/
    adr/
    threat-model/
```

## 2.3 Technology baseline

Use current stable releases at implementation time.

| Layer | Baseline |
|---|---|
| Mobile | React Native, Expo, TypeScript, React Navigation, TanStack Query |
| Web | Next.js, TypeScript, accessible component primitives |
| API | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Cache/jobs | Redis and a supported task worker |
| Object storage | S3-compatible encrypted storage with signed URLs |
| Identity | Managed OpenID Connect/OAuth provider |
| Video | BAA-capable vendor through adapter; local mock for development |
| Interoperability | HL7 FHIR R4 adapter |
| API documentation | OpenAPI 3 |
| Observability | OpenTelemetry-compatible traces, metrics, and logs |
| Infrastructure | Docker for local development; Terraform for production |
| CI | GitHub Actions or equivalent |

# 3. Actors and authorization

## 3.1 Roles

| Role | Description |
|---|---|
| Patient | Accesses own profile, appointments, messages, records, and prescriptions |
| Authorized caregiver | Future role; accesses delegated data within explicit scope |
| Clinician | Accesses assigned/authorized patients and appointments |
| Clinical staff | Supports clinician workflows under organization policy |
| Support agent | Resolves account and scheduling issues using minimum necessary access |
| Operations administrator | Manages configuration and integration health |
| Security auditor | Read-only access to approved audit data |
| System service | Performs scoped background jobs and integrations |

## 3.2 Authorization rules

- The system shall deny access by default.
- Authorization shall evaluate role, organization, patient relationship, appointment/encounter context, purpose, and record sensitivity.
- A user shall never receive another patient’s data through object identifiers, search, caching, logs, exports, or notifications.
- Workforce access shall require MFA.
- Privileged support access shall require a reason code and shall be audited.
- Break-glass access, if introduced, shall require explicit justification, notification, and retrospective review.
- Administrative users shall not edit signed clinical content unless a separately authorized amendment workflow exists.

# 4. Functional requirements

Priorities: **P0** MVP, **P1** next release, **P2** future.

## 4.1 Authentication and session management

| ID | Priority | Requirement |
|---|---|---|
| AUTH-001 | P0 | The system shall authenticate users through a managed OIDC provider. |
| AUTH-002 | P0 | The system shall require verification of the patient’s email or phone before protected information is displayed. |
| AUTH-003 | P0 | The system shall require MFA for clinician, support, admin, and auditor accounts. |
| AUTH-004 | P0 | The system shall use short-lived access tokens and securely rotated refresh tokens. |
| AUTH-005 | P0 | The mobile app shall store credentials only in platform secure storage. |
| AUTH-006 | P0 | The system shall support password recovery without revealing whether an account exists. |
| AUTH-007 | P0 | The system shall allow users to view and revoke active sessions. |
| AUTH-008 | P0 | Sensitive profile or security changes shall require recent authentication. |
| AUTH-009 | P0 | Repeated failed authentication shall trigger rate limits and risk controls. |
| AUTH-010 | P0 | Sign-out shall revoke the local session and clear protected local caches. |

## 4.2 Registration, profile, consent, and safety

| ID | Priority | Requirement |
|---|---|---|
| ONB-001 | P0 | The patient shall be able to create an account with minimum required demographic information. |
| ONB-002 | P0 | The system shall store Terms, Privacy Notice, Telehealth Consent, and communication-preference acceptance with version, timestamp, and actor. |
| ONB-003 | P0 | The system shall present a visible notice that the service is not for emergencies. |
| ONB-004 | P0 | Configured high-risk symptom selections shall interrupt normal navigation and show emergency guidance. |
| ONB-005 | P0 | The system shall capture the patient’s timezone and preferred language. |
| ONB-006 | P0 | The system shall support accessibility preferences such as reduced motion and larger text. |
| ONB-007 | P0 | The patient shall be able to manage communication preferences independently by channel. |
| ONB-008 | P0 | The patient shall be able to view consent history and submit a withdrawal request where supported. |
| ONB-009 | P0 | The system shall validate and normalize patient address and phone data. |
| ONB-010 | P1 | The system shall support dependent and caregiver invitations with explicit delegation. |

## 4.3 Clinician directory and discovery

| ID | Priority | Requirement |
|---|---|---|
| DISC-001 | P0 | The patient shall be able to search clinicians by name, specialty, and configured concern synonyms. |
| DISC-002 | P0 | The patient shall be able to filter by specialty, availability, language, visit type, price range, and rating. |
| DISC-003 | P0 | The system shall exclude clinicians who are not eligible to serve the patient’s confirmed location. |
| DISC-004 | P0 | Search results shall show verified name, credentials, specialty, rating summary, price, and next availability. |
| DISC-005 | P0 | The patient shall be able to sort by recommended, soonest availability, rating, and price. |
| DISC-006 | P0 | Empty results shall provide removable filters and alternative navigation. |
| DISC-007 | P0 | Recommendation logic shall be explainable with non-clinical reasons such as specialty match, availability, language, and distance. |
| DISC-008 | P1 | The system shall support organization and facility filters. |
| DISC-009 | P1 | The system shall support accessibility and interpretation availability filters. |

## 4.4 Clinician profile

| ID | Priority | Requirement |
|---|---|---|
| PROF-001 | P0 | The system shall display clinician credentials, specialty, organization, languages, experience, visit types, and availability. |
| PROF-002 | P0 | The system shall display a rating summary and approved reviews without exposing reviewer identity. |
| PROF-003 | P0 | The system shall display service-area or location eligibility before booking. |
| PROF-004 | P0 | The system shall display estimated self-pay price or coverage status with an explanatory disclaimer. |
| PROF-005 | P0 | The patient shall be able to start booking from the profile. |
| PROF-006 | P1 | The patient shall be able to save clinicians as favorites. |

## 4.5 Availability and appointments

| ID | Priority | Requirement |
|---|---|---|
| APT-001 | P0 | Clinicians or authorized staff shall be able to define recurring availability, exceptions, visit duration, and buffer time. |
| APT-002 | P0 | Available slots shall be generated using timezone-aware timestamps. |
| APT-003 | P0 | The booking service shall prevent overlapping clinician appointments through database constraints and transactional logic. |
| APT-004 | P0 | Selecting a slot shall create a time-limited hold before confirmation. |
| APT-005 | P0 | Appointment creation shall support idempotency keys. |
| APT-006 | P0 | Confirmation shall show clinician, date, time, timezone, visit type, price/coverage, policy, and preparation instructions. |
| APT-007 | P0 | The patient shall be able to view upcoming and past appointments. |
| APT-008 | P0 | The patient shall be able to cancel or reschedule according to configured policy. |
| APT-009 | P0 | Clinician cancellation shall trigger patient notification and alternative booking options. |
| APT-010 | P0 | The system shall record appointment status transitions and actor. |
| APT-011 | P0 | Calendar export shall exclude diagnosis and sensitive concern data. |
| APT-012 | P1 | The system shall support a waitlist and earlier-slot notifications. |

## 4.6 Waiting room and visit readiness

| ID | Priority | Requirement |
|---|---|---|
| WAIT-001 | P0 | The patient shall be able to enter the waiting room only within a configurable appointment window. |
| WAIT-002 | P0 | The system shall confirm patient identity and current physical location before joining. |
| WAIT-003 | P0 | The system shall confirm valid telehealth consent before media access. |
| WAIT-004 | P0 | The app shall test microphone, camera, speaker/audio route, and network quality. |
| WAIT-005 | P0 | Permission-denied states shall include platform-specific recovery instructions. |
| WAIT-006 | P0 | The waiting room shall display clinician, appointment time, status, and delay information. |
| WAIT-007 | P0 | The patient shall be able to upload approved documents while waiting. |
| WAIT-008 | P0 | Uploaded files shall be type-validated, size-limited, malware-scanned, encrypted, and associated with the appointment. |
| WAIT-009 | P0 | Leaving the waiting room shall not cancel the appointment. |
| WAIT-010 | P1 | The waiting room shall support interpretation and accessibility service indicators. |

## 4.7 Video consultation

| ID | Priority | Requirement |
|---|---|---|
| CALL-001 | P0 | The backend shall issue short-lived, appointment-scoped media tokens only to authorized participants. |
| CALL-002 | P0 | The call shall support microphone mute, camera toggle, camera switch, audio route, in-call chat, and end call. |
| CALL-003 | P0 | The system shall display connection quality without exposing technical details that confuse the user. |
| CALL-004 | P0 | The app shall attempt automatic reconnection after transient failure. |
| CALL-005 | P0 | The user shall be able to switch to audio-only mode when video quality is inadequate. |
| CALL-006 | P0 | A failed call shall offer retry, audio alternative, and support contact. |
| CALL-007 | P0 | The system shall record join, leave, reconnect, and end timestamps without recording media. |
| CALL-008 | P0 | Ending the call shall transition the encounter to a follow-up state and revoke media tokens. |
| CALL-009 | P0 | Recording shall be disabled in MVP. |
| CALL-010 | P1 | The call shall support live captions or an approved accessibility integration. |

## 4.8 Secure messaging

| ID | Priority | Requirement |
|---|---|---|
| MSG-001 | P0 | Authorized patients and care-team users shall be able to exchange messages in scoped threads. |
| MSG-002 | P0 | A thread shall identify its participants and care context. |
| MSG-003 | P0 | The system shall support unread state and delivery timestamp. |
| MSG-004 | P0 | Attachments shall use the same secure upload controls as waiting-room documents. |
| MSG-005 | P0 | The system shall prohibit PHI in push, SMS, and email notification previews. |
| MSG-006 | P0 | The system shall retain messages according to configured policy. |
| MSG-007 | P0 | Deleted user interfaces shall not remove records that must be retained. |
| MSG-008 | P0 | Users shall be able to report inappropriate content or contact support. |
| MSG-009 | P1 | The system shall support message templates for approved non-clinical content. |

## 4.9 Records and documents

| ID | Priority | Requirement |
|---|---|---|
| REC-001 | P0 | The patient shall be able to list authorized records by type, date, source, and status. |
| REC-002 | P0 | The patient shall be able to search and filter records. |
| REC-003 | P0 | The system shall display record provenance and service date. |
| REC-004 | P0 | Record download shall require active authorization and shall produce an audit event. |
| REC-005 | P0 | Downloads shall use short-lived signed URLs or streamed authorization. |
| REC-006 | P0 | The system shall not expose internal storage paths. |
| REC-007 | P0 | Unavailable records shall show a reason and support path. |
| REC-008 | P0 | FHIR-imported records shall preserve source identifiers and last-updated timestamps. |
| REC-009 | P1 | The system shall render selected structured lab results with reference ranges and source disclaimers. |
| REC-010 | P1 | The patient shall be able to submit a record correction request. |

## 4.10 Prescriptions and pharmacy fulfillment

| ID | Priority | Requirement |
|---|---|---|
| RX-001 | P0 | The patient shall be able to view authorized prescription records. |
| RX-002 | P0 | The system shall display source-provided medication name, strength, form, quantity, instructions, prescriber, refills, and status. |
| RX-003 | P0 | The product shall not independently calculate or modify dosage instructions. |
| RX-004 | P0 | Expired, cancelled, unavailable, and exhausted-refill states shall be visually and semantically distinct. |
| RX-005 | P0 | The patient shall be able to choose an available pharmacy pickup or delivery option where integration supports it. |
| RX-006 | P0 | Fulfillment-request status shall be stored separately from medication status. |
| RX-007 | P0 | A failed fulfillment request shall not modify the original prescription record. |
| RX-008 | P0 | Controlled-substance prescribing and EPCS shall be excluded from MVP. |
| RX-009 | P1 | The system shall support refill-request routing to the authorized clinician. |

## 4.11 Notifications

| ID | Priority | Requirement |
|---|---|---|
| NTF-001 | P0 | The system shall support in-app, push, email, and optional SMS notification channels. |
| NTF-002 | P0 | Notification content outside the authenticated app shall be generic and free of PHI. |
| NTF-003 | P0 | Notifications shall include appointment confirmation, reminder, cancellation, delay, message availability, record availability, and prescription availability. |
| NTF-004 | P0 | Users shall be able to configure channels subject to mandatory service/security notices. |
| NTF-005 | P0 | Failed notification delivery shall be retried with bounded backoff and observable status. |
| NTF-006 | P1 | The system shall support configurable reminder schedules by organization. |

## 4.12 Clinician portal

| ID | Priority | Requirement |
|---|---|---|
| CLN-001 | P0 | Clinicians shall authenticate with MFA. |
| CLN-002 | P0 | Clinicians shall manage profile and availability subject to organization approval. |
| CLN-003 | P0 | Clinicians shall view only authorized appointment queues and patient context. |
| CLN-004 | P0 | Clinicians shall start and end visits. |
| CLN-005 | P0 | Clinicians shall view patient-uploaded documents associated with the appointment. |
| CLN-006 | P0 | Clinicians shall send secure messages. |
| CLN-007 | P0 | Clinicians shall upload or link an encounter summary, record, and non-controlled prescription artifact. |
| CLN-008 | P0 | Clinicians shall not silently change signed content; amendments shall preserve history. |
| CLN-009 | P1 | Clinicians shall configure team coverage and delegated inbox rules. |

## 4.13 Operations and administration

| ID | Priority | Requirement |
|---|---|---|
| ADM-001 | P0 | Support users shall search accounts and appointments using minimum necessary fields. |
| ADM-002 | P0 | Privileged access shall require a reason code and shall be audited. |
| ADM-003 | P0 | Administrators shall activate, suspend, or deactivate clinicians without deleting historical records. |
| ADM-004 | P0 | Administrators shall manage specialties, visit types, policies, and notification templates. |
| ADM-005 | P0 | Operations users shall view integration health and failed-job queues. |
| ADM-006 | P0 | Security auditors shall have read-only access to approved audit queries. |
| ADM-007 | P0 | Admin actions shall use four-eyes approval for high-risk configuration where configured. |
| ADM-008 | P1 | The system shall support organization-level tenant configuration and branding. |

# 5. State models

## 5.1 Appointment state machine

```text
draft
  -> held
  -> confirmed
  -> checked_in
  -> waiting
  -> in_progress
  -> completed

confirmed/checked_in/waiting
  -> rescheduled
  -> cancelled_by_patient
  -> cancelled_by_clinician
  -> no_show

held
  -> expired
```

Rules:

- Every transition shall record timestamp, actor, reason, and previous state.
- Invalid transitions shall return a conflict response.
- Rescheduling shall retain linkage to the prior schedule instance.
- Completed appointments shall not be deleted.

## 5.2 Video-session state machine

```text
created -> token_issued -> joining -> connected
connected -> reconnecting -> connected
joining/reconnecting -> failed
connected -> ended
```

## 5.3 Prescription fulfillment state machine

```text
not_requested -> requested -> accepted -> processing -> ready_or_dispatched -> completed
requested/accepted/processing -> failed_or_cancelled
```

The fulfillment state shall not overwrite the clinical medication status.

# 6. Data requirements

## 6.1 Core entities

| Entity | Key fields |
|---|---|
| User | id, identity_provider_id, status, role bindings, created_at |
| PatientProfile | user_id, legal name, DOB, contact, address, timezone, language |
| Practitioner | id, name, credentials, identifiers, status |
| PractitionerRole | practitioner, organization, specialty, service area, languages |
| Organization | id, name, type, tenant settings |
| AvailabilityRule | practitioner, recurrence, duration, timezone, exceptions |
| Appointment | patient, practitioner, organization, start/end, status, visit type |
| Encounter | appointment, status, start/end, summary reference |
| VideoSession | appointment, vendor reference, state, timestamps |
| Consent | patient, type, version, status, accepted_at, withdrawn_at |
| MessageThread | participants, context, status |
| Message | thread, sender, body ciphertext/reference, sent_at, status |
| MedicalRecord | patient, type, source, service date, status, FHIR identifiers |
| Document | owner/context, storage key, mime type, hash, scan status |
| Prescription | patient, prescriber, medication fields, status, source identifiers |
| FulfillmentRequest | prescription, pharmacy/option, status, external reference |
| InsurancePolicy | patient, payer, member identifiers, verification status |
| Notification | recipient, channel, template, status, non-PHI payload |
| AuditEvent | actor, action, resource type/id, purpose, outcome, timestamp, metadata |
| SupportCase | subject, category, status, assigned user, minimum necessary notes |

## 6.2 Data integrity

- All primary identifiers shall be non-sequential opaque UUIDs or equivalent.
- Patient-clinician relationships shall be validated server-side.
- Appointment overlap prevention shall be enforced in the database as well as application logic.
- Mutable clinical artifacts shall use versioning or immutable amendment records.
- All timestamps shall be stored in UTC and rendered in the user’s timezone.
- Uploaded documents shall store a cryptographic hash and malware-scan status.
- External identifiers shall include source system and namespace.
- Soft deletion shall be used where retention or audit history is required.

## 6.3 FHIR mapping baseline

| CareConnect entity | FHIR R4 resource |
|---|---|
| Patient profile | Patient |
| Clinician | Practitioner |
| Clinician organization/specialty | PractitionerRole, Organization |
| Appointment | Appointment |
| Visit | Encounter |
| Lab result | DiagnosticReport, Observation |
| Document | DocumentReference |
| Prescription | MedicationRequest |
| Allergy | AllergyIntolerance |
| Message/notification context | Communication |
| Audit | AuditEvent |

The adapter shall isolate FHIR versions and vendor-specific profiles from internal domain models.

# 7. API requirements

## 7.1 General API rules

- Base path: `/api/v1`.
- JSON request/response with UTF-8.
- OpenAPI documentation generated from source.
- Bearer access token from OIDC provider.
- Every write endpoint shall validate authorization and input server-side.
- Idempotency keys shall be supported for appointment booking, fulfillment requests, and other retry-sensitive writes.
- Pagination shall be cursor-based for large lists.
- Errors shall use a consistent structure:

```json
{
  "error": {
    "code": "APPOINTMENT_SLOT_UNAVAILABLE",
    "message": "That time is no longer available.",
    "request_id": "opaque-id",
    "details": {}
  }
}
```

- Error details shall not include secrets, stack traces, or protected information.
- API responses containing protected data shall use `Cache-Control: no-store`.

## 7.2 Representative endpoints

### Patient and consent

```text
GET    /me
PATCH  /me/profile
GET    /me/sessions
DELETE /me/sessions/{session_id}
GET    /me/consents
POST   /me/consents
POST   /me/account-closure-requests
```

### Discovery

```text
GET /specialties
GET /practitioners
GET /practitioners/{id}
GET /practitioners/{id}/availability
```

### Appointments

```text
POST   /appointment-holds
POST   /appointments
GET    /appointments
GET    /appointments/{id}
POST   /appointments/{id}/check-in
POST   /appointments/{id}/reschedule
POST   /appointments/{id}/cancel
POST   /appointments/{id}/calendar-export
```

### Video

```text
POST /appointments/{id}/device-check
POST /appointments/{id}/video-token
POST /appointments/{id}/video-events
POST /appointments/{id}/end-visit
```

### Messaging

```text
GET  /message-threads
POST /message-threads
GET  /message-threads/{id}/messages
POST /message-threads/{id}/messages
POST /message-threads/{id}/read
```

### Records and documents

```text
GET  /records
GET  /records/{id}
POST /documents/upload-intents
POST /documents/{id}/complete
GET  /documents/{id}/download
```

### Prescriptions

```text
GET  /prescriptions
GET  /prescriptions/{id}
GET  /prescriptions/{id}/fulfillment-options
POST /prescriptions/{id}/fulfillment-requests
POST /prescriptions/{id}/refill-requests
```

### Clinician

```text
GET   /clinician/appointments
GET   /clinician/appointments/{id}
POST  /clinician/availability
PATCH /clinician/appointments/{id}/status
POST  /clinician/encounters/{id}/documents
POST  /clinician/encounters/{id}/prescriptions
```

### Admin

```text
GET  /admin/users
GET  /admin/appointments
GET  /admin/audit-events
GET  /admin/integrations/health
POST /admin/practitioners/{id}/suspend
```

# 8. External interface requirements

## 8.1 Identity provider

- Support OIDC authorization code flow with PKCE for mobile.
- Support OIDC web flow with secure HTTP-only cookies for web.
- Support MFA for workforce users.
- Support account disablement and token revocation.
- Do not copy password hashes into CareConnect.

## 8.2 Video provider

The adapter shall support:

- room/session creation;
- participant-scoped short-lived tokens;
- join/leave webhooks;
- connection-quality events;
- audio-only mode;
- regional routing where available;
- no recording by default;
- BAA and documented data-flow review for production.

## 8.3 Notifications

- Push through APNs/FCM.
- Email/SMS through approved vendors.
- Templates shall be server-controlled and reviewed for PHI exposure.
- Delivery callbacks shall update status.
- Tokens and phone/email destinations shall be treated as sensitive data.

## 8.4 EHR/FHIR

- Support OAuth/SMART-on-FHIR where required by the source.
- Validate FHIR resources and preserve provenance.
- Use retry and dead-letter queues for transient failures.
- Do not overwrite source records; maintain synchronization metadata.
- Support organization-specific mapping configuration.

## 8.5 Pharmacy/laboratory

- Use adapter interfaces and synthetic provider implementations for development.
- Validate webhook signatures.
- Preserve external status and timestamps.
- Do not treat external availability as guaranteed until confirmation.
- Exclude EPCS in MVP.

# 9. Non-functional requirements

## 9.1 Performance

| ID | Requirement |
|---|---|
| PERF-001 | Mobile cold start shall target < 3 seconds on representative supported devices. |
| PERF-002 | Authenticated API requests shall target p95 < 300 ms excluding third-party latency. |
| PERF-003 | Search results shall render within 2 seconds under normal load. |
| PERF-004 | Video join shall target < 15 seconds after user action under acceptable network conditions. |
| PERF-005 | Lists shall use pagination and virtualization where needed. |
| PERF-006 | Document downloads shall support resumable or recoverable behavior for large files where practical. |

## 9.2 Availability and resilience

| ID | Requirement |
|---|---|
| REL-001 | Production API availability target shall be 99.9% monthly. |
| REL-002 | The system shall use health checks and automated restart/replacement. |
| REL-003 | Third-party failures shall degrade only the affected capability when possible. |
| REL-004 | Background jobs shall be idempotent and retry with bounded exponential backoff. |
| REL-005 | Failed jobs shall enter an observable dead-letter path. |
| REL-006 | The mobile app shall show recoverable offline states and avoid destructive retries. |
| REL-007 | Target recovery point objective shall be ≤ 15 minutes. |
| REL-008 | Target recovery time objective shall be ≤ 1 hour for the primary region. |

## 9.3 Scalability

- Services shall be stateless except for approved data stores.
- The API and workers shall scale horizontally.
- Media traffic shall flow through the video provider rather than the application API.
- Database indexes shall support patient, clinician, appointment time, status, and audit queries.
- Capacity tests shall cover 10× pilot traffic before general launch.

## 9.4 Accessibility

- Patient and web applications shall target WCAG 2.2 AA.
- Mobile implementations shall follow WCAG-to-mobile guidance and platform accessibility APIs.
- Automated tests shall be supplemented by manual screen-reader and keyboard testing.
- No critical task shall depend on drag-and-drop, color alone, or precision gestures.
- Text scaling shall not truncate headers or primary actions.

## 9.5 Compatibility

- Support the latest two major iOS versions feasible at launch and a documented Android API range.
- Support current stable Chrome, Edge, Safari, and Firefox for web portals.
- Publish an explicit supported-device and browser matrix.
- Gracefully block unsupported versions with upgrade guidance.

# 10. Security and privacy requirements

## 10.1 Security baseline

- Use OWASP ASVS Level 2 as the web/API verification baseline.
- Use OWASP MASVS controls for the mobile application.
- Perform threat modeling for identity, multi-tenancy, appointment authorization, document access, video tokens, notifications, and integrations.
- Conduct static analysis, dependency scanning, secret scanning, container scanning, and dynamic application testing in CI/CD.
- Complete an independent penetration test before production launch.

## 10.2 Encryption and secrets

- TLS 1.2+ shall be required; prefer TLS 1.3.
- Database, backups, object storage, and queues shall be encrypted at rest.
- Production encryption keys shall be managed by a cloud KMS and separated by environment.
- Secrets shall be stored in a secrets manager, never source control or mobile bundles.
- Signed URLs shall be short-lived and bound to authorization context where possible.
- Mobile local protected data shall use platform secure storage and encrypted persistence.

## 10.3 Application controls

- Validate and normalize all input.
- Use parameterized queries/ORM protections.
- Enforce authorization at the service layer for every resource access.
- Protect web sessions against CSRF and session fixation.
- Configure secure headers and content security policy.
- Rate-limit authentication, search abuse, uploads, messaging, and token creation.
- Validate upload MIME type by content, not filename.
- Scan uploaded files before making them available.
- Do not render active content from uploaded documents.
- Use anti-automation and anomaly detection proportionate to risk.

## 10.4 Logging and audit

Application logs:

- shall use structured JSON;
- shall include request/correlation ID;
- shall not include access tokens, passwords, message bodies, diagnosis, medication names, document contents, or full patient identifiers;
- shall use centralized redaction and allowlisted fields.

Audit logs:

- shall be append-only or tamper-evident;
- shall record actor, action, resource, purpose/reason, timestamp, source, and outcome;
- shall record protected-data views and downloads, not only modifications;
- shall support retention and export for authorized review;
- shall alert on suspicious patterns such as bulk access or repeated denied access.

## 10.5 Privacy operations

- Maintain a system data inventory and data-flow diagram.
- Classify data and apply minimum-necessary collection.
- Support access/export/correction/closure workflows subject to applicable rules.
- Maintain vendor/subprocessor inventory and BAA status.
- Define retention by data category and jurisdiction.
- Test incident and breach-response procedures.
- Prevent production data from entering development, test, analytics, or support tools without approved controls.

# 11. Deployment and operations

## 11.1 Environments

- local;
- development;
- integration;
- staging;
- production.

Each environment shall use separate credentials, data stores, keys, and vendor projects. Production data shall not be copied to lower environments.

## 11.2 Local development

Docker Compose shall provide:

- PostgreSQL;
- Redis;
- object-storage emulator or local S3-compatible service;
- API;
- worker;
- mail catcher;
- synthetic FHIR server or mock;
- mock video and notification adapters.

A single documented command shall start the backend development environment.

## 11.3 Production baseline

A cloud deployment shall include:

- private network segmentation;
- managed PostgreSQL with multi-zone configuration;
- encrypted object storage;
- managed Redis;
- API and worker services in private subnets where applicable;
- WAF/API gateway or ingress controls;
- KMS and secrets manager;
- centralized logs, metrics, traces, and alerting;
- automated backups and point-in-time recovery;
- infrastructure as code;
- controlled deployment approvals and rollback.

## 11.4 CI/CD gates

Every pull request shall run:

- formatting and linting;
- type checking;
- unit tests;
- API contract tests;
- database migration checks;
- secret and dependency scanning;
- mobile/web accessibility checks where automatable;
- build of all applications.

Release pipelines shall additionally run:

- integration and E2E tests;
- container scan;
- migration dry run;
- deployment to staging;
- smoke tests;
- approved production promotion;
- post-deployment health verification and rollback readiness.

# 12. Verification and test requirements

## 12.1 Test layers

| Layer | Minimum expectation |
|---|---|
| Unit | Domain services, policies, validators, state transitions |
| Integration | Database, Redis, storage, identity claims, adapters |
| Contract | OpenAPI clients and external adapter contracts |
| Mobile UI | Component and navigation tests |
| Web UI | Component and accessibility tests |
| E2E | Patient booking/joining and clinician completion vertical slice |
| Security | Authorization, IDOR, rate limits, upload, session, token tests |
| Performance | Search, booking contention, messages, document access |
| Resilience | Vendor timeout, webhook duplication, queue retry, database failover |
| Accessibility | Automated plus manual keyboard, screen reader, text scaling |
| Recovery | Backup restore and disaster-recovery exercise |

## 12.2 Mandatory E2E scenarios

1. New patient registration, verification, consent, and profile completion.
2. Search and filter clinician directory.
3. Book a slot while a competing request attempts the same slot.
4. Reschedule and cancel with policy confirmation.
5. Enter waiting room, deny then grant permissions, upload a valid document.
6. Join mock video, simulate weak network, reconnect, switch to audio, end visit.
7. Send and receive a secure message.
8. View and download an authorized record.
9. Attempt to access another patient’s record and receive denial without data leakage.
10. View prescription and submit a fulfillment request.
11. Clinician manages availability and completes a visit.
12. Support user performs privileged lookup with reason code.
13. Audit user verifies sensitive actions are recorded.
14. Notification delivery contains no PHI.
15. Backup is restored into an isolated environment and validated.

## 12.3 Coverage and defect gates

- Critical domain modules shall have ≥ 80% branch coverage.
- Coverage is not a substitute for security and E2E testing.
- Zero open critical/high security findings at release.
- Zero known cross-user authorization defects.
- Zero critical accessibility defects in primary journeys.
- All P0 requirements shall have a passing test or documented manual verification.

# 13. Error handling requirements

- User-facing errors shall state what happened, what remains safe, and the next action.
- Retryable and non-retryable errors shall be distinguished.
- The UI shall preserve entered data after recoverable failures.
- Duplicate user actions shall not create duplicate records.
- Third-party error messages shall not be shown directly.
- Every error response shall include a request ID for support.
- Authentication expiry shall return the user safely to sign-in without exposing cached protected screens.
- Offline mode shall prevent actions that require server confirmation and shall not falsely show success.

# 14. Observability and service-level objectives

## 14.1 SLOs

| Service indicator | Objective |
|---|---|
| API successful request rate | 99.9% monthly |
| Booking correctness | 99.99% without duplicate confirmed slots |
| Notification enqueue success | 99.9% |
| Video token issuance | 99.9% |
| Audit event persistence | 99.99% |
| Background job successful completion | 99.5% within retry window |

## 14.2 Alerts

Alert on:

- sustained API error rate or latency;
- authentication anomaly;
- appointment conflict;
- audit pipeline failure;
- object malware-scan backlog;
- FHIR/pharmacy/video webhook failure;
- queue depth;
- backup failure;
- database storage or replication risk;
- abnormal record-download volume;
- release health regression.

Alerts shall exclude PHI and link to protected operational tools.

# 15. Requirement traceability

Each implementation issue shall reference:

- PRD epic;
- SRS requirement ID;
- design screen or component;
- API endpoint/event;
- automated test;
- security/privacy consideration.

Example:

```text
Feature: Patient books appointment
PRD: Epic C
SRS: APT-002 through APT-006
Design: Slot Selection, Confirmation
API: POST /appointment-holds, POST /appointments
Tests: E2E-03, AUTHZ-APT-01, LOAD-BOOK-01
```

# 16. Definition of done

A feature is done only when:

- acceptance criteria and linked SRS requirements pass;
- UI covers loading, empty, error, offline, success, and permission states;
- authorization is enforced server-side;
- audit behavior is implemented where required;
- analytics contain no PHI;
- accessibility checks pass;
- tests are added and green;
- API/OpenAPI and user documentation are updated;
- threat model or privacy impact is updated when the data flow changes;
- no secrets or real patient data are committed;
- the change is deployable and rollback is documented.

# 17. References

1. U.S. HHS, [Summary of the HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html).
2. U.S. HHS Telehealth, [HIPAA Rules for telehealth technology](https://telehealth.hhs.gov/providers/telehealth-policy/hipaa-for-telehealth-technology).
3. U.S. HHS, [Guidance on Risk Analysis](https://www.hhs.gov/hipaa/for-professionals/security/guidance/guidance-risk-analysis/index.html).
4. HL7, [FHIR R5 Appointment resource](https://fhir.hl7.org/fhir/Appointment/) and implementation compatibility guidance; internal integration baseline remains FHIR R4 unless a target partner requires another version.
5. ONC, [Fast Healthcare Interoperability Resources](https://healthit.gov/interoperability/investments/fhir/).
6. W3C, [Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/).
7. W3C, [Guidance on Applying WCAG 2.2 to Mobile Applications](https://www.w3.org/TR/wcag2mobile-22/).
8. OWASP, [Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/).
9. OWASP, [Mobile Application Security Verification Standard](https://mas.owasp.org/MASVS/).