# FDR Sentinel architecture

Current implementation map, based on source `0894f53`. This is a local synthetic system,
not an approved bank/AICTE integration. See [status](docs/STATUS.md) for historical executed
checks and [verification](docs/VERIFICATION.md) for the current CI diagnosis.

The shared architecture diagram appears once in the [README architecture section](README.md#architecture).

## The core choice

A **modular monolith with asynchronous workers**, not a fleet of microservices. FastAPI
owns controlled state transitions; PostgreSQL is authoritative. Celery performs durable
background work. Independent humans retain registration, clearance, approval and issuance
authority. The [original blueprint](docs/ARCHITECTURE_BLUEPRINT.md) is preserved separately;
its proposed technologies and future work are not all present in the implementation.

## Components and source map

| Component | Responsibility | Source anchor |
|---|---|---|
| React + TypeScript + Vite | Maker, reviewer and operator workspace; calls authenticated APIs | `apps/web/src/` |
| Keycloak | OIDC authorization-code flow with PKCE; API JWT verification | `scripts/bootstrap.py`, `apps/api/sentinel/auth.py` |
| FastAPI + SQLAlchemy | Typed commands, scope checks, versions, idempotency and decisions | `apps/api/sentinel/main.py`, `services.py`, `schemas.py` |
| PostgreSQL | Records, evidence metadata, policy snapshots, history, audit and transactional outbox | `apps/api/sentinel/models.py`, `apps/api/migrations/` |
| Private S3-compatible SeaweedFS | Immutable original document bytes; content hashes retained in database | `docker-compose.yml`, `apps/api/sentinel/storage.py` |
| Redis + Celery | Queue dispatch, scheduled jobs and retryable work | `apps/api/sentinel/jobs.py`, `transactions.py` |
| ClamAV + PyMuPDF + Tesseract | Malware scan, digital extraction, OCR and evidence coordinates | `apps/api/sentinel/storage.py`, `extraction.py`, `jobs.py` |
| Rules and human review | Provisional APH fixtures, discrepancy/correction and independent decisions | `apps/api/sentinel/compliance.py`, `policies/`, `services.py` |
| Fictional source sandbox | Independent ledger/registry, signed HTTP responses and reconciliation | `apps/api/sentinel/sandbox_app.py`, `integrations.py` |
| SMTP + Mailpit | Captured local notifications, retries and reminder evidence | `apps/api/sentinel/delivery.py`, `docker-compose.yml` |
| Browser-only demo | Shared UI with separate synthetic state, no backend authority | `apps/web/src/demo/` |

Source filenames identify responsibility, not proof of test passage. See the acceptance
map and exact source tree for individual scenario coverage.

## Intake to decision

1. An authenticated institution records its context, obligation and instrument. Monetary
   values are integer INR paise, not floating-point rupees.
2. Bounded PDF intake stores the immutable original in private object storage and records
   its SHA-256. Database state and outbox work are committed transactionally.
3. The worker scans the document. Pending, rejected or failed scanning stays blocked.
   Digital extraction or Tesseract OCR produces evidence-linked fields after scan success.
4. Deterministic, versioned provisional rules evaluate the record. Unknown policy context
   requires review. Optional AI can propose fields but cannot make a decision.
5. Independently initiated source checks query a separate **fictional** ledger/registry.
   The request ID, attempts, response status and compared fields are retained.
6. A different authorized reviewer accepts registration or returns the record with a
   reason. Corrections/superseding evidence retain earlier originals and decisions.

Registration acceptance is neither bank confirmation nor permission to release funds.

## Lifecycle operations

- **Maturity:** configurable bands, deduplicated captured SMTP reminders and operational
  follow-up. A synthetic clock used in demonstrations must be disclosed.
- **Renewal/replacement:** a later covering instrument and independent authorization;
  original evidence and lineage remain. Replacement is not a refund.
- **Release case:** evidence readiness, current scoped PGRC/Vigilance/Grants clearances,
  holds and independent approval precede a separate type-authorized issuer.
- **Synthetic output:** an NOC/sanction PDF carries no real financial authority. Subsequent
  sandbox receipt/reconciliation never asserts real RELEASED or moves funds.
- **Reports/interventions:** complete-scope totals, pagination, audited safe CSV, product
  deadlines, acknowledgement, escalation and retained resolved episodes. Acknowledgement
  cannot change source facts or waive a hold.

## Security boundaries

Identity is insufficient by itself: the API checks role plus institution, case and bureau
scope. Maker/checker separation, version checks and idempotency protect commands. Private
object access is authorized; original evidence, reasons and actors remain traceable.
Operator provisioning does not confer financial decision authority or evidence access.

Compose applies a read-only API/worker filesystem, writable bounded `/tmp`, dropped
capabilities and no-new-privileges. Service ports bind loopback. The local environment is
not production-qualified: TLS, approved encryption/KMS, identity assurance, retention,
security assessment and incident/recovery ownership remain external acceptance work.
The source sandbox's fixture administrator credential is separate from portal access.

## Implemented versus proposed

The local stack uses SeaweedFS through the S3 interface, not the blueprint's original
MinIO choice. Frontend dependencies are the actual React/OIDC/Vite package set; the
blueprint's TanStack Query, React Hook Form, Zod and shadcn list is not a dependency claim.
No Kafka, Kubernetes, blockchain or autonomous approval model is required. Optional local
Ollama support is disabled by default and is not exercised merely by showing this diagram.

Authorized real-source integration, exhaustive legal coverage, representative impact
measurement and production operation are not delivered by a sandbox demonstration.
See [requirement coverage](docs/PROBLEM_STATEMENT_COVERAGE.md),
[architecture decisions](docs/ARCHITECTURE_DECISIONS.md) and the
[historical blueprint](docs/ARCHITECTURE_BLUEPRINT.md) for rationale and open work.
