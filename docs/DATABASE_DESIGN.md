# Database design

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

Application role has no schema ownership in production. Local owner migrations are
convenient but not a substitute for production grants. Audit database owner attacks
require external immutable anchoring and separation of duties in Phase 4.

## Later schema (do not create empty tables prematurely)

Phase 2: extracted_fields, corrections, discrepancies, verification_requests/attestations.
Phase 3: obligations, policy_versions/rules activation registry, instrument_relationships,
release_cases, clearance_requirements/decisions, holds, notifications and lifecycle_events.
Phase 4: audit checkpoints, retention/holds and restoration metadata.
Full bank references require envelope encryption and managed key rotation before storage.

Backups: encrypted snapshots + WAL/PITR in production; test restore into separate database,
verify counts and audit continuity. RPO/RTO are sponsor decisions, not invented guarantees.


## Adopted independent review amendments

Separate obligations from deposit_records now. Deposit type is FDR/RPGF/RTGS/ONLINE/OTHER_LEGACY; online records have no invented maturity. Identity roles live only in many scoped role_bindings with enabled and validity dates, not principals.role. Scope types INSTITUTION/BUREAU/CASE are reserved; bureau decision authority also requires case/institution assignment. Phase 1B brings release_cases, clearances, holds, lineage and notifications forward. Evaluation freshness is (input_revision, policy_revision, document_set_hash); command version is distinct. Multipart fingerprints use verified bytes SHA and category; stable response/object IDs on replay. Unreferenced private objects need grace-period reconciliation. HMAC key version is stored; eventual managed-key encrypted canonical references require authorized reconciliation, redacted access and dual-key rotation.
