# Database design

## SIH completion additions

`integration_requests` persists source operation, immutable declaration/policy context,
input revision, initiator, W3C context, remote correlation, attempts/next time, result and
signature. Pending work commits with its audit before network processing. A trigger
protects request identity and terminal evidence. Processor no-autoflush ensures sealing
the result and completion metadata in one transaction. Signed response validation is
separate from source authenticity: this source is explicitly a synthetic sandbox.

`notification_deliveries` has one row per notification, stable Message-ID, PENDING/SENT/
DEAD_LETTER, attempts/next time/error and SMTP-accepted timestamp. It is a durable delivery
outbox. At-least-once semantics are explicit for crash-after-SMTP-before-DB-commit.

Independent `sandbox.registry`, `sandbox.ledger` and `sandbox.requests` use a separate
database role/schema and independent immutable fictional records. The source role only
updates ledger reservation and injected-failure counter columns; it has no core-table
permissions. Core runtime has no sandbox-schema access. No full real financial reference
is introduced. Local sandbox ledger IDs refer to fictional records, independently of
masked portal declarations.

`OPERATOR` is a technical BUREAU/PLATFORM binding. The security-definer assignment command
uses a fixed search path, validates active operator/target/scope and bounded validity,
disallows self/MAKER/OPERATOR grants, and appends audit atomically. Execute permission is
explicit; direct runtime role-binding updates and arbitrary financial authority remain
forbidden. Schema head after these additions: `52b01026`.

PostgreSQL is authoritative. Alembic owns schema evolution; no create_all at startup.
UUID identifiers, UTC timestamptz, INR integer paise, explicit date-only banking dates.
Indexes cover tenant/list/queue/foreign keys. No real financial seed records.

## Phase 1 entities

| Table | Ownership and invariants |
|---|---|
| principals | OIDC subject unique, enabled flag; no global role and no passwords |
| institutions | AICTE-like synthetic identifier unique, legal name, governance/programme/land/context, academic year; owner subject; initial registry state DECLARED |
| role_bindings | Principal, role, scope_type INSTITUTION/BUREAU/CASE, scope_id, enabled, validity; multiple scopes; operator-provisioned privileges |
| security_deposit_obligations | Institution FK, regulatory_event, context, policy snapshot, independent obligation status |
| deposit_records | Tenant FK, bank code, reference_last4 + keyed reference digest unique per bank, amount >0, type FDR/RPGF/RTGS/ONLINE/OTHER_LEGACY; FDR dates required, others optional; obligation FK; separate workflow/verification/lifecycle, command version and input_revision, maker |
| documents | Instrument+institution composite FK, random immutable object key, SHA256, size/MIME, uploader; QUARANTINED/READY/REJECTED/FAILED; scan provenance and evidence JSON; no arbitrary URL |
| evaluations | Instrument FK, immutable input snapshot/hash, policy/algorithm hashes, findings and evidence references, outcome PASS/FAIL/REVIEW; UTC created time |
| review_decisions | Instrument FK, actor, disposition/reason, evaluated version, evaluation FK; append only |
| audit_events | Tenant, actor, action, aggregate, snapshot, request ID/time; trigger rejects update/delete by normal runtime role |
| outbox_events | Document processing event, attempts, published_at; PostgreSQL SKIP LOCKED publisher; at-least-once delivery |
| idempotency_records | Principal + method/path + key unique, request SHA, response JSON/status; committed with mutation |

Institution and document relationships must never rely on a client-supplied tenant ID
without parent authorization. Submitted FDR fields and originals have no update route.
Returns move back to DRAFT. Explicit correction changes input_revision. New immutable documents invalidate evaluation. Evaluation stores input_revision, policy_revision, document_set_hash and evaluated_at; evaluation does not change input_revision.

## Transaction and storage boundaries

Locked ORM reads explicitly use populate_existing: waiting for a row lock must refresh
the identity-map value, otherwise optimistic-version checks can observe stale memory.
Clearance history has (case_id, bureau, input_revision) uniqueness and append-only
triggers. Document original identifiers/hash/object key are guarded against UPDATE.
Case input revisions are independent of deposit input revisions.

Sensitive services lock the aggregate SELECT FOR UPDATE, check version/state, append
decision/evaluation/audit/outbox and increment version in one transaction. Unique
idempotency records serialize concurrent same-key requests (database advisory transaction
lock); different keys still meet aggregate locks. Same key + different payload = 409.
Response serialization is saved before commit. Exceptions roll back all database effects.

Object upload cannot join a database transaction. Upload to a unique private key, then
commit metadata/outbox. Failed commit can leave an unreachable orphan; later reconciliation
deletes only unreferenced objects after a grace period. Never expose keys to callers.
Worker reads immutable bytes, verifies SHA, scans and extracts before setting READY.
Scan/error status and audit are persisted in the same worker transaction.

The local application uses a restricted runtime role without schema ownership,
deletion or history-update privileges. Owner credentials are confined to provisioning/
test containers, not API/worker/Beat. Audit database-owner attacks still require external
immutable anchoring and production separation of duties.

## Implemented extensions and deferred schema

Phase 1B added release_cases, clearance_decisions, holds, instrument_relationships
and notifications. Required bureau sets live in the immutable case snapshot, with
revision-keyed append-only decisions. Phase 2 added extraction_corrections,
discrepancies and verification_attestations. Raw typed extraction stays in documents
JSON with page/offset/bounds/hash provenance. Phase 3 uses repository policy manifests
and frozen evaluations instead of redundant empty activation/event tables. Phase 4A
adds outbox trace_context and isolated restore manifests; schema head is
`339cf1735fc9`. There are 19 domain tables plus alembic_version.

External audit checkpoints and sponsor-defined retention/deletion remain deferred;
no deletion operation exists and legal/financial holds continue to block issuance.
Full bank references require envelope encryption and managed key rotation before storage.

Backups: encrypted snapshots + WAL/PITR in production; test restore into separate database,
verify counts and audit continuity. RPO/RTO are sponsor decisions, not invented guarantees.


## Adopted independent review amendments

Separate obligations from deposit_records now. Deposit type is FDR/RPGF/RTGS/ONLINE/OTHER_LEGACY; online records have no invented maturity. Identity roles live only in many scoped role_bindings with enabled and validity dates, not principals.role. Scope types INSTITUTION/BUREAU/CASE are reserved; bureau decision authority also requires case/institution assignment. Phase 1B brings release_cases, clearances, holds, lineage and notifications forward. Evaluation freshness is (input_revision, policy_revision, document_set_hash); command version is distinct. Multipart fingerprints use verified bytes SHA and category; stable response/object IDs on replay. Unreferenced private objects need grace-period reconciliation. HMAC key version is stored; eventual managed-key encrypted canonical references require authorized reconciliation, redacted access and dual-key rotation.
