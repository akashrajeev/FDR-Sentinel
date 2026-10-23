# Requirements and evidence matrix

Status is maintained in STATUS.md. Planned tests are not passing-test claims.

| ID | Requirement / baseline capability | Phase | Acceptance evidence |
|---|---|---|---|
| R01 | FastAPI/React/TypeScript modular monolith, PostgreSQL | 1 | API integration on PostgreSQL, TS build, migration restart |
| R02 | Redis/Celery asynchronous work | 1 | Outbox to broker, replay-safe scan task, retry tests |
| R03 | Protected documents | 1 | Scope denials, size/signature validation, private MinIO, malware/failure quarantine |
| R04 | Versioned deterministic cited policies | 1/3 | Pure rule fixtures; unknown/effective-year tests; frozen evaluation hashes |
| R05 | OCR and AI assistance, evidence links | 1 digital / 2 OCR+AI | Page/bounds/hash evidence; no-evidence review; labeled extraction evaluation |
| R06 | Registration and verification | 1/2 | Onboarding -> FDR -> upload -> submit -> officer review |
| R07 | Maturity, renewal/replacement, release/refund | 3 | D4-D7 including no automatic release |
| R08 | Secure auth, role + resource control, audit | 1/4 | Real OIDC signature/issuer/audience validation; cross-tenant/role denials; immutable audit |
| R09 | Simulated vs authorized bank/AICTE | 2 | SIMULATED attestation/UI; production adapter gate; no actual payment |
| R10 | Human decisions | 1/3 | Worker cannot accept registration; independent bureau/final approval tests |
| R11 | Docker, tests, observability | 1/4 | Compose health, CI, readiness/metrics/request IDs; later trace/restore/load evidence |
| R12 | Transactions, concurrency, idempotency | 1 | Same-key replay/conflict; lock versions; audit/outbox atomic rollback |
| R13 | Alerts/dashboards/reports | 1 work queue / 3 | Scope queue, D4 idempotent notifications, reporting totals |
| D1 | Submission with editable proposed extraction | 1 partial / 2 | Phase 1 exact evidence + registration; Phase 2 corrections |
| D2 | Cross-document discrepancy + disposition | 2 | Known mismatch and human correction fixture |
| D3 | Contextual 35-lakh UG, private lease 2x | 1 limited | Supported fixture tests with citation; exceptions REVIEW |
| D4 | 90/30/7 product-policy reminders | 3 | Injected clock, repeat run produces no duplicates |
| D5 | Renewal/replacement lineage | 3 | Old record retained; authorizer and evidence required |
| D6 | PGRC pending blocks release | 3 | API attempts denied in each blocking state |
| D7 | Authorized synthetic NOC/sanction | 3 | Separate signatories/type-specific branch; no bank movement |
| D8 | Scope and replay controls | 1/3 | Tenant isolation; role denial; later bureau-scope matrix |
| D9 | Bank source distinction | 1 manual / 2 adapter | MANUALLY_REVIEWED not BANK_CONFIRMED; SIMULATED labels |
| D10 | Observable failures | 1 processing / 4 full | Scan outages never ready; retries tracked; later OCR/connector/notification traces |

The ten public-brief capability categories in ARCHITECTURE.md are treated as sponsor
requirements. The listed public mirror is not an authenticated sponsor acceptance
specification; confirmation with SIH/AICTE remains necessary before production scope freeze.
