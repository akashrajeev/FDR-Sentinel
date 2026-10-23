# Local operation and production activation

This runbook operates the synthetic local system. STATUS.md records executed results.
No command below grants real bank, AICTE or financial authority.

## Startup and identity

Run `python scripts/bootstrap.py`, then `docker compose up --build -d`.
Bootstrap preserves existing credentials and generates missing keys. Never commit or
share `.env`, `.local/realm.json`, backups or uploads. Open http://localhost:8088.
Read the generated `DEMO_<USER>_PASSWORD` locally; the README lists demo account roles.
Initial ClamAV definitions can take minutes. Check `docker compose ps` and
`curl http://localhost:8088/api/v1/health/ready` before demonstrating uploads.

One API, two Celery processes and one Beat scheduler form the modular monolith.
Migrations/provisioning use the database owner; running API/worker/Beat use
`sentinel_runtime`. Its grants permit required inserts and selected mutable updates,
but no DDL, deletes, history rewrites or privileged scope assignment. Onboarding can
only insert its own MAKER institution scope. This is defense in depth; authorization
still resides in the application, not PostgreSQL row-level security.

Keycloak 26.8.1 is pinned. This workspace was upgraded by stopping the old instance,
archiving its data, copying the original `sih26265_keycloak-data` volume to
`sih26265_keycloak-data-v2`, and starting the new version against the copy. The old
volume and ignored `.local/backups/keycloak-before-26.8.1.tar.gz` remain available.
Fresh installations create the v2 volume and import the generated realm. For local
rollback, stop Keycloak and restore the old image/mount together; do not run the older
binary against a database already migrated by the new binary. Never delete volumes
as a troubleshooting shortcut. This embedded development IdP database is unsuitable
for a production IdP deployment.

Use `scripts/local.py scripts/grant_scope.py --help` for operator scope provisioning.
The CLI requires a known OIDC subject, explicit institution/case/bureau, a reason and
optional expiry; it audits changes. No API provides officer self-enrollment. Disable
principal/scope access through controlled operator procedures. Access JWTs have a
short lifetime; do not claim instantaneous IdP session revocation from JWT validation.

## Processing and incident triage

Readiness reports `degraded_intake_available` when Redis, scanner or recent worker
heartbeat is unavailable. Database/private-storage failure makes readiness unavailable.
An intake success records the document and transactional outbox; it does not mean the
document was scanned or authenticated. No unsafe file content can be downloaded.

Inspect `docker compose logs --tail 100 api worker beat clamav` using request/trace IDs.
Documents remain quarantined on processing failure. The worker performs bounded retry;
after five failures the scoped officer can use Retry processing in document intelligence.
Fix the cause first. Retrying never approves registration or release. Outbox publication
is at least once, with locked replay-safe processing and database-specific queues.
Do not run a second Beat scheduler for the same database.

`scripts/local.py scripts/outage_drill.py` stops/restarts actual Redis and ClamAV in a
`finally` recovery path and uploads synthetic records. Run only on the dedicated local
stack, without concurrent browser qualification. It verifies degraded intake, denied
unsafe download, recovery and exactly one retained draft document per attempt.

Logs contain template routes, status, duration, request IDs and OTel IDs, not token,
query, financial-reference, SQL or document text. Native FastAPI automatic telemetry
is disabled to prevent URL query capture. Outbox stores W3C trace context and Celery
continues the upload trace; baggage is not propagated. JSON spans export locally.
Optional `OTEL_EXPORTER_OTLP_ENDPOINT` forwards to an operator-configured collector;
that remote collector path has not been exercised. Protect collectors/log retention.
Internal `/metrics` is not exposed through the web gateway. Processing errors appear
in task status/dead letters; approval remains a human operation.

## Restore and measurements

Run `.venv\Scripts\python scripts/local.py scripts/restore_drill.py` on Windows after
installing the locked Python environment. It exports a consistent PostgreSQL snapshot,
dumps it and restores a new `sentinel_restore_<random>` database, copies referenced
original/preview objects to a new private bucket, compares every table count and verifies
every SHA-256. It writes an ignored dump and manifest with dump hash under `.local/backups/`.
Source data is retained, and generated targets are never overwritten. Protect these
artifacts like the source. This verifies local logical recovery; it does not implement
encrypted off-site copies, immutable audit anchoring, PITR or production RPO/RTO.

Run `.venv\Scripts\python scripts/local.py --test scripts/load_check.py` separately
from tests. It refuses any database other than `sentinel_test`, seeds 1,000 synthetic
institutions/deposits and probes a temporary real HTTP API with the restricted DB role.
It reports read latency/errors, then terminates only its own API process. It preserves
fixture rows; repeated runs grow the dedicated test database. Results do not establish
upload/OCR throughput or production capacity. See MEASUREMENTS.md for actual numbers.

Runtime traces, local outage and restore drills are reproducible. Local files are not
an independent immutable audit sink; production anchoring and restore credentials need
separate owners. No automatic deletion exists: original evidence/history is retained.
Financial/legal holds block issuance and require explicit human evidence to resolve.
A sponsor-approved retention schedule must precede any deletion implementation.

## Approval assurance and production gates

`DECISION_MFA_REQUIRED=true` requires a signed IdP access-token `amr` containing `otp`,
`webauthn` or `hwk`, and a recent integer `auth_time` (default maximum age 300 seconds),
before approval/issuance can mutate. The local demo defaults to `DECISION_MFA_REQUIRED=false`.
Header/client claims cannot satisfy this check. The production IdP must actually
enforce MFA and map trusted methods/authentication time; this demo realm has not been
qualified for enrollment, step-up, recovery or assurance. Do not merely add an `amr`
mapper that asserts MFA without enforcement. Negative endpoint tests and pure freshness
tests cover the application gate; there is no claimed successful real MFA ceremony.

`ENVIRONMENT` values other than `development` fail startup. Keep that gate until:

* A policy owner reviews current official amendments, source hashes, legal effective
  dates, historical/aggregate contexts, required bureaus and authorized signatories.
* Bank/AICTE agreements, authentic contracts/credentials, callback/reconciliation rules
  and written authorization replace simulated/unconnected adapters.
* Approved institutional identity proof, IdP/MFA, TLS/ingress limits, managed secret/key
  rotation, storage encryption/region, retention and incident ownership are established.
* Independent security testing, current image/package review, external immutable audit,
  backup/PITR and sponsor-approved recovery/load objectives are satisfied.

No actual release/settlement endpoint exists. The database prohibits BANK_CONFIRMED and
RELEASED in this implementation. Synthetic PDFs do not move money, and no AI/worker can
record bureau, approval or issuance decisions. An activation change needs its own
reviewed implementation and evidence; toggling an environment variable is insufficient.
