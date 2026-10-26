# Test strategy

Registry UI acceptance adds the public desktop/mobile home, absence of private API
requests before login, actual OIDC continuation, server-backed record/workflow filtering,
mobile record layout and return to the full register. All earlier browser workflows
remain real-service checks. Specific records are found through scoped search rather
than assuming they are in a six-row overview. Unique Mailpit subject search preserves
SMTP evidence when a retained mailbox has future-dated entries after a clock rollback.
Neither tests nor presentation may bypass role validity, stale evidence or human gates.

Phase 6: `tests/test_operations.py` exercises actual PostgreSQL policy history/scope,
stale/idempotent configuration, missing/unsafe evidence, discrepancy/unknown review,
actual source NOT_FOUND, bureau/hold follow-up, custom maturity bands, acknowledgement
versus resolution, recurrence, concurrent scan deduplication, safe scoped pagination/CSV,
real SMTP escalation and revoked queued-delivery cancellation. Browser acceptance adds
policy configuration -> independent escalation -> CSV -> acknowledgement -> READY source
resolution. `benchmark_workflow.py` uses real network services and fixed synthetic labels;
its scripted proxy must never be presented as observed human work. Exact actual runs
are recorded in STATUS.md; this paragraph alone is not passing-test evidence.

SIH completion adds actual HTTP exchanges against a separately persisted sandbox and
actual SMTP plus Mailpit mailbox-content assertions. Adverse cases include source
signature/correlation, missing/mismatched data, HTTP 503, delayed result, stale declaration,
cross-scope/operator denial, CSV rollback/replay and refused SMTP through dead letter and
recovery. Backend network tests run both against the normal stack and a clean source
export with fresh isolated credentials/volumes. No SQLite substitutes core PostgreSQL.

Browser coverage includes new onboarding → registry → operator assignment → CSV intake;
clock/reminder → actual email → independent renewal; and underfunded scrutiny → denied
acceptance → return → correction/superseded evidence → fresh evaluation/disposition →
acceptance. Source receipt/reconciliation follows human issuance in the browser. Old
echo-only fixture controls are excluded from the presentation UI. See SIH_ACCEPTANCE.md.

Tests must report actual commands, counts and dependency versions in STATUS.md. A mock
unit test is never evidence that object storage, Keycloak, Redis or PostgreSQL actually connected.

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
* Documents: real private S3-compatible write/read, invalid MIME/magic/oversize/too-many pages,
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
typecheck/build and real browser workflows (workflow configured; remote CI not yet run).
The transport-failure browser test intercepts only to drop the response after a real
API commit, then verifies real replay identity; it never fabricates a server response.
Recent-MFA unit tests cover missing/stale/future/present method claims, and actual
OIDC endpoint tests deny mutation with the gate enabled. No successful MFA ceremony
is claimed. Runtime SQL denies DDL, history rewrites and officer scope grants.
Trace tests assert query exclusion and eager outbox parent context; the outage drill
separately checks actual broker-to-worker trace correlation. Load fixtures and tests
must run sequentially against the preserved dedicated test DB.
Do not broaden tests for low-impact prose changes; rerun gates after
relevant code/configuration changes. Failed infrastructure checks are recorded honestly.


## Adopted independent review amendments

Add E1 deficient submission/return/correction; E2 RTGS/ONLINE without maturity; E3 new document invalidates prior evaluation; E4 PGRC/Vigilance and independent final signatory gate SYNTHETIC issuance; E5 closure/merger/conversion evidence and holds; E6 simultaneous stale commands only one succeeds; E7 Redis/ClamAV outage truthfully degraded, no unsafe read; E8 extraction sample size/precision/recall and measured workflow durations. Use realistic synthetic PDFs and separate truth labels; no fabricated impact baseline.
