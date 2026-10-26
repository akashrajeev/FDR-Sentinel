# Security model

Operational follow-up grants no financial authority. Only assigned REVIEWERs can change
an institution's product SLA/supervisor or manually scan/acknowledge. Policies are
append-only and revision-checked; a supervisor must already have an independent active
scope. Scheduled scans use current authorization time even for synthetic future-clock
demonstrations. Recipients are rechecked before SMTP; stale/revoked work is CANCELLED.
Acknowledgement cannot resolve findings/holds, accept registration or authorize release.
Case-only report scope does not grant institution access. Exports are audited, formula-safe
and bounded. Financial rule applicability and production startup gates remain unchanged.

## SIH connected-service boundary

The bank/AICTE sandbox is a real network service over independently administered
fictional records. A separate database role/schema forbids its access to core tables
and forbids core runtime access to source tables. Client API key, fixture-admin key and
response-signing key are separate generated credentials. The portal runtime receives
no fixture-admin, database-owner, IdP-admin or demo-user passwords. Sandbox writes are
restricted to fictional identifiers; fixture mutation is disallowed. Signed response
source/protocol, time, body fingerprint and correlations are validated before use.
Request/result evidence is immutable after completion; late evidence is explicitly STALE.
The assumed local HMAC protocol is not genuine bank PKI or an official interface contract.

Technical OPERATOR scope is not an institution assignment or approval role. Server auth
provides its subject to a narrow DB security-definer command with fixed search path,
explicit execute grants, active-principal/scope checks, expiry, reason and atomic audit.
Self grants, MAKER grants and OPERATOR grants are excluded. Direct role-binding DML by
runtime remains blocked. Permanent maker/checker and independent issuer checks still apply.

CSV ingest is bounded, strict and scoped; preview hashes prevent changed-file commit,
and the mutation/idempotency transaction prevents partial intake or duplicate replay.
CSV never sets accepted, verified, paid or released states. Full reference input remains
transient; masking/HMAC protection is reused.

SMTP transport is real but constrained to the local Mailpit host/loopback and fictional
.invalid recipients; no relay is configured. Delivery retries/dead letters are auditable.
Stable Message-ID aids correlation but is not an exactly-once SMTP guarantee. A transport
acceptance does not mean a human read the message. All source and delivery operations are
separate from regulatory/financial decisions; actual BANK_CONFIRMED and RELEASED stay
prohibited. Source reconciliation can only follow an independently human-issued output.

## Trust and identity

Browser, uploaded files, OCR text, model outputs and external callbacks are untrusted.
Keycloak/approved IdP authenticates; FastAPI verifies RS256 signature, explicit issuer,
audience, expiry and subject using pinned configured JWKS URL. Never trust token role or
tenant claims alone. Server assignments determine permissions. Unknown subjects may
onboard only as institution makers; privileged identities need operator provisioning.
Disabled identities fail closed. Portal uses PKCE and memory-held tokens; no localStorage
tokens or application-issued JWTs. IdP reset/logout/revocation behavior must be qualified
before production (short token lifetimes, MFA and session policy).

INSTITUTION: create own declared institution, create/upload/evaluate/submit its FDRs.
OFFICER: assigned-institution read/evaluate and accept/return submissions; cannot create
institution/FDR or upload as maker. AUDITOR: assigned-institution read only.
Maker and checker subjects must differ even if assignments change later. No global
admin token gives financial decision authority. Bank integration and workers have no
interactive decision endpoint credential. Release scopes and bureau separation are implemented.

## Threats and controls

| Threat | Control / residual risk |
|---|---|
| IDOR and tenant leakage | Parent-scope lookup on every API and object download; 404 for invisible IDs; composite tenant FK; negative tests |
| Forged/stale JWT | JWKS signature + issuer/audience/expiry; explicit local subject grants; configurable recent verified MFA gate for approval/issuance; actual production IdP assurance remains unqualified |
| Duplicate/replayed financial action | Durable principal/operation idempotency, payload hashes, aggregate lock/version checks, database constraints |
| Malicious document | Only bounded PDF multipart, magic/parse/page checks, private quarantine, ClamAV before extraction, worker limits; scanner outage stays unavailable |
| XSS/token theft | React escaping, CSP, no HTML rendering of extraction, memory token; dependencies pinned; no remote document content execution |
| CSRF | Bearer header auth without application auth cookies; strict same-origin proxy/CORS; IdP state+PKCE handled by OIDC library |
| SSRF/exfiltration | No user document URL fetch; object keys server generated; JWKS/storage URLs operator configured; future AI needs explicit data policy |
| Prompt injection | Optional local model has bounded schema-only output, independent source anchoring, no tools or approval credentials |
| False verification | MANUALLY_REVIEWED label; no BANK_CONFIRMED from manual/worker path; adapters visibly SIMULATED or NOT_CONNECTED |
| Audit tampering | Append-only API + trigger; audit within same mutation transaction; DB owner remains privileged; external checkpoint Phase 4 |
| Secret leakage | Generated ignored .env, no fixture passwords in source, private network dependencies, no auth/document data in logs |
| Policy error | Cited source/hash, narrow applicability, frozen inputs, unknown REVIEW; provisional fixture cannot authorize regulatory release |
| Broker outage/races | Transactional outbox retry, SKIP LOCKED publisher, replay-safe locked worker, scan hash verification |

## Storage and operational boundaries

Phase 2 enforces typed local-model output and independent source anchoring, with no
model tools or decision credentials. Original model quote failures are not hidden as
accurate extraction. Human corrections retain document SHA, page, bounded coordinates,
transcription, proposer/checker, reason and original extraction. Correction confirmation
changes input_revision; a fresh evaluation and discrepancy disposition are mandatory.
Private previews are rendered in the scanned-document worker, hash checked on access
and scoped through the API. No unscanned PDF parsing occurs in the web request path.
Failed processing stays quarantined, including after the fifth/dead-letter attempt.

Private S3-compatible SeaweedFS bucket without anonymous policy; random keys never returned. Authenticated
downloads use attachment + nosniff, only READY files. Originals immutable by application
behavior; production versioning/object-lock and encryption require deployment review.
TLS terminates at production ingress; local localhost HTTP is explicitly development
only. Do not expose Compose dependency ports on public interfaces. Production startup
must not use dev realm, test client, fixture adapters or development credentials.

Antivirus definitions must be current; scanner readiness and signature age are deployment
gates. Resource limits include 10 MiB upload, 30 PDF pages and bounded processing time.
Rate limits at ingress and authentication endpoint are required for production; local
OIDC brute-force protection is configured. No regulatory production claims before
penetration testing, backup restoration, key rotation, retention policy and incident drill.
Retention terms/data locality require sponsor/legal approval; do not invent a legal period.

Runtime containers receive an explicit minimal environment rather than all `.env`
values. Database-owner, Keycloak-admin, runtime-provisioning and demo-user passwords
are excluded from API/worker/Beat. Containers run as uid 10001 with read-only root,
bounded /tmp, dropped capabilities and no-new-privileges. PostgreSQL runtime grants
deny DDL, deletion and history rewrites; owner/operator compromise remains outside
that boundary. OTLP export is optional; default payload-free JSON spans propagate
via transactional outbox to worker, with no baggage or URL query capture.

See OPERATIONS_RUNBOOK.md for the optional verified-MFA gate, synthetic exemption,
retained evidence, isolated restoration and explicit production activation blockers.


## Adopted independent review amendments

No single global role: identities have many role_bindings (principal, role, scope_type, scope_id, enabled, valid_from/until). Institution self-service grants only own institution maker scope, never bureau/officer. PGRC cannot decide Vigilance; each bureau decision also needs case/institution scope. Maker/checker and independent signatory compare permanent subjects even if roles change. Readiness allows durable intake during broker outage and reports degraded processing. Scanner outage never permits read/approval. Fake bank source remains SIMULATED, never BANK_CONFIRMED.
