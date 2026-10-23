# Test strategy

Tests must report actual commands, counts and dependency versions in STATUS.md. A mock
unit test is never evidence that MinIO, Keycloak, Redis or PostgreSQL actually connected.

## Phase 1 gates

* Pure rules: base Engineering UG 35 lakh, private lease 2x, govt/aided exemption,
  unknown year/history/programme -> REVIEW, insufficient amount -> FAIL, stable hashes.
* Real PostgreSQL API integration: onboarding, FDR registration/duplicates, private
  upload metadata, evaluation, submission, officer return/acceptance, persisted audit.
* JWT: real Keycloak token accepted, forged/wrong audience/expired/disabled denied;
  server assignment overrides spoofed role claims; no institution scope impersonation.
* Scope: institution A cannot list/read/write/download B, unassigned officer denied,
  institution cannot review, auditor cannot mutate, same-subject maker/checker denied.
* Idempotency/concurrency: exact replay one row/event, changed payload 409, two workers
  same event one processing result, stale version 409, decision/audit rollback together.
* Documents: real private MinIO write/read, invalid MIME/magic/oversize/too-many pages,
  scanner EICAR detection test, unavailable scanner never READY, document hash tamper,
  retries after failure, digital-PDF page/bounds evidence, no text -> human review.
* Frontend: generated OpenAPI types, `tsc`, production Vite build, browser login with
  PKCE and API workflow across maker/officer; no request interception that fakes results.
* Operations: migration fresh DB and restart, Compose config/health, `/health/ready`
  covers database/broker/storage, metrics/request IDs, outbox publication after outage.

Use synthetic PDF fixtures generated in tests, not committed institutional records.
Database test URL must name a dedicated disposable database; tests must refuse shared
or production URLs. No SQLite substitution. Test-only Keycloak direct grant client may
get tokens in integration tests; portal always uses authorization code + PKCE.

## Later gates

Phase 2: OCR precision/recall and evidence quality by field/type on labeled fixtures,
adversarial content, signed demo attestation source labels, corrections with provenance.
Phase 3: clock-injected reminders; lineage; every forbidden transition; bureau scope;
independent signatory; all holds; four release document categories; RTGS vs FDR outputs.
Phase 4: D1-D10 end-to-end, threat-focused abuse, measured load and queue backlog,
restore drill, signature/key rotation, retention/legal holds and external audit anchoring.

CI uses Linux Docker dependencies, migrations and Python integration tests plus frontend
typecheck/build. Do not broaden tests for low-impact prose changes; rerun gates after
relevant code/configuration changes. Failed infrastructure checks are recorded honestly.
