# Security model

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
interactive decision endpoint credential. Release roles/bureaus are Phase 3.

## Threats and controls

| Threat | Control / residual risk |
|---|---|
| IDOR and tenant leakage | Parent-scope lookup on every API and object download; 404 for invisible IDs; composite tenant FK; negative tests |
| Forged/stale JWT | JWKS signature + issuer/audience/expiry, no algorithm fallback; explicit local subject grants; later MFA assurance for financial roles |
| Duplicate/replayed financial action | Durable principal/operation idempotency, payload hashes, aggregate lock/version checks, database constraints |
| Malicious document | Only bounded PDF multipart, magic/parse/page checks, private quarantine, ClamAV before extraction, worker limits; scanner outage stays unavailable |
| XSS/token theft | React escaping, CSP, no HTML rendering of extraction, memory token; dependencies pinned; no remote document content execution |
| CSRF | Bearer header auth without application auth cookies; strict same-origin proxy/CORS; IdP state+PKCE handled by OIDC library |
| SSRF/exfiltration | No user document URL fetch; object keys server generated; JWKS/storage URLs operator configured; future AI needs explicit data policy |
| Prompt injection | No model in first slice; future extraction is data-only typed output, never tools/approval authority |
| False verification | MANUALLY_REVIEWED label; no BANK_CONFIRMED from manual/worker path; future mocks SIMULATED and denied in production |
| Audit tampering | Append-only API + trigger; audit within same mutation transaction; DB owner remains privileged; external checkpoint Phase 4 |
| Secret leakage | Generated ignored .env, no fixture passwords in source, private network dependencies, no auth/document data in logs |
| Policy error | Cited source/hash, narrow applicability, frozen inputs, unknown REVIEW; provisional fixture cannot authorize regulatory release |
| Broker outage/races | Transactional outbox retry, SKIP LOCKED publisher, replay-safe locked worker, scan hash verification |

## Storage and operational boundaries

MinIO private bucket without anonymous policy; random keys never returned. Authenticated
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


## Adopted independent review amendments

No single global role: identities have many role_bindings (principal, role, scope_type, scope_id, enabled, valid_from/until). Institution self-service grants only own institution maker scope, never bureau/officer. PGRC cannot decide Vigilance; each bureau decision also needs case/institution scope. Maker/checker and independent signatory compare permanent subjects even if roles change. Readiness allows durable intake during broker outage and reports degraded processing. Scanner outage never permits read/approval. Fake bank source remains SIMULATED, never BANK_CONFIRMED.
