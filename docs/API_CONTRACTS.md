# API contracts

Phase 6 operational endpoints (real authenticated API, product SLAs only):

- GET/POST `/institutions/{id}/operations-policy`: scoped read; REVIEWER-only append
  with expected_revision, reason, bounded hour thresholds, maturity day bands and
  pre-existing independent supervisor subject. Mutations require Idempotency-Key.
- POST `/operations/scan`: scoped REVIEWER, institution_id and optional timezone-aware
  synthetic as_of within ten years. Same transactional service as scheduled Celery.
- GET `/reports/interventions`: institution/deposit/category/state/overdue filters,
  after/limit keyset pagination, full filtered counts and next_cursor. Case-only scopes
  see only assigned-case tasks. Observation time is distinct from report retrieval time.
- GET `/reports/interventions.csv`: corresponding filters, safe audited CSV capped at
  10,000 rows; exceeding the cap fails explicitly. Source detail and IDs are retained.
- POST `/interventions/{id}/acknowledge`: independent REVIEWER institution scope, reason
  and Idempotency-Key; one acknowledgement per OPEN task, never source resolution.
- GET `/interventions/{id}/notifications`: scoped reminder/escalation recipients and
  actual SMTP delivery state/attempts. No foreign institution or platform-operator access.
- GET `/notifications` accepts an optional kind filter, separating maturity UI from
  operational notices. All other institution/resource authorization remains mandatory.

## Connected SIH sandbox, operator and delivery extensions

All portal routes below use the same OIDC/scoped authorization and mutation idempotency
as the core. Sandbox states never become BANK_CONFIRMED or RELEASED.

| Route | Contract |
|---|---|
| GET `/sandbox/catalogue` | Authenticated read of published fictional source examples, through real sandbox HTTP |
| POST `/institutions/{id}/registry-check` | Maker/reviewer; queue registry lookup; optional NORMAL/DELAYED/TRANSIENT_FAILURE transport behavior |
| POST `/deposits/{id}/bank-check` | Reviewer; expected_version, independent ledger_id, behavior; immutable declaration snapshot and durable request |
| GET `/integration-requests?institution_id=&deposit_id=&case_id=` | Scoped progress, attempts, source result and remote correlation |
| POST `/integration-requests/{id}/retry` | Reviewer/issuer; dead-letter attempt count in expected_version; retains request identity |
| POST `/release-cases/{id}/sandbox-exchange` | Recorded human issuer, ISSUED_SYNTHETIC, fresh clearance/hold gates; no ledger_id sends case receipt; ledger_id requests bank sandbox reconciliation |
| GET `/operator/workspace` | Technical operator metadata and scope assignments; no financial/document authority |
| POST `/operator/assignments` | Operator, target principal, role, institution/case/bureau, validity <=90 days and reason; self/operator-role grants prohibited; DB-atomic audit |
| GET `/legacy-import/template` | Authenticated UTF-8 CSV header template |
| POST `/legacy-import/preview` | Maker multipart CSV <=200 KiB/200 rows; strict schema, scope, dates, duplicates; SHA256/count/total, no writes |
| POST `/legacy-import/commit` | Same CSV + expected_sha256 and Idempotency-Key; atomic DRAFT-only intake |
| GET `/notifications?deposit_id=` | Scoped persisted alerts and actual SMTP delivery attempts/status |
| POST `/notifications/{id}/retry` | Reviewer, dead-letter attempt count as expected_version; no approval side effects |

Independent source service at localhost:8092 has `/health`, authenticated
`GET /v1/catalogue`, `POST /v1/requests`, `GET /v1/requests/{id}` and separately
admin-authenticated immutable `/v1/fixtures/registry` and `/v1/fixtures/ledger`.
This is an assumed local protocol, not an official bank/AICTE API specification.
Normal portal credentials cannot write source fixtures. The source database role
cannot read core tables; the core runtime cannot read the sandbox schema.

Responses carry HMAC-authenticated source/protocol, timestamp, request fingerprint,
client correlation and remote identity. Polling is implemented; no fake callback
completion or genuine bank PKI is claimed. Late results become STALE after declaration
changes. Pending, stale, failed and conflicting initiated checks block acceptance/issuance;
successful checks do not replace a human decision. Reconciliation never changes actual
financial-release state. SMTP acceptance is a transport result, not proof of reading.

Base `/api/v1`. Runtime OpenAPI `/openapi.json` is exported to `openapi/` and used to
generate the frontend schema types. JSON dates ISO 8601; money `amount_paise` integer.
OIDC access token in Authorization Bearer; server never issues identity tokens.
Browser uses Authorization Code + PKCE. No password grant in the portal.

## First slice

| Method and path | Actor | Request / result |
|---|---|---|
| GET /me | Authenticated | Provisioning info, role and assigned institution IDs |
| POST /institutions | Institution | legal_name, external_id, governance, programme, land, academic_year, exceptional_context; creates DECLARED institution + caller assignment |
| GET /institutions | Scoped | Assigned institution list |
| GET /institutions/{id} | Scoped | Institution detail |
| POST /deposits | Institution maker | obligation_id, deposit_type, bank_code, reference (transient), amount_paise, FDR issue_date/maturity_date or other deposited_on; returns masked typed deposit DRAFT |
| GET /deposits | Scoped | Bounded list; optional institution_id |
| GET /deposits/{id} | Scoped | FDR with documents, evaluations, review decisions |
| POST /deposits/{id}/documents | Institution maker | multipart PDF <=10 MiB; immutable private object; returns QUARANTINED metadata |
| GET /documents/{id}/content | Scoped | Authenticated streamed PDF attachment only if READY; audited access |
| POST /deposits/{id}/evaluate | Scoped writer | expected_version; stores cited deterministic evaluation; bumps version |
| POST /deposits/{id}/submit | Institution maker | expected_version; READY document + current validation; -> PENDING_SCRUTINY even with substantive FAIL/REVIEW |
| POST /deposits/{id}/review | Assigned OFFICER | expected_version, decision ACCEPT_REGISTRATION/RETURN, reason >=10 chars; -> ACCEPTED or DRAFT; no bank/release certification |
| GET /audit-events | Scoped | Bounded tenant events; no unscoped financial logging |
| GET /work-queue | OFFICER | Assigned PENDING_SCRUTINY deposits |
| GET /health/live | Public | Process health |
| GET /health/ready | Public | Dependency readiness; 503 without internals if unavailable |
| GET /metrics | Internal network | Operational counts/durations; no institution IDs or references |

All mutations require `Idempotency-Key` (8-128 safe characters). Exact replay returns
original response; changed body yields 409. Header absent/invalid = 422. Review/evaluate/
submit require expected_version; stale version/state conflict = 409. Tenant-invisible
objects return 404; authenticated role violations 403; invalid JWT 401; validation 422;
oversized upload 413; dependency failures 503. Failed requests are not cached as success.
List endpoints return up to 100 newest items in the first slice; cursor pagination is a
later reporting requirement and this bounded behavior is explicit.

Errors are `{detail: string | validation-errors, request_id?: string}`. Request IDs in
`X-Request-ID` response and logs; no token, reference, PDF text or private key in logs.

Registration acceptance means the officer reviewed the stored evidence and provisional
rule result. It never creates bank confirmation, regulatory eligibility, NOC or payment.
Unknown/provisional policy yields REVIEW and is displayed to the officer; known FAIL
blocks acceptance, while safe deficient records may enter scrutiny. Missing document extraction requires human evidence review.

## Lifecycle milestone contracts

Phase 3 adds GET `/policies/current`, POST `/deposits/{id}/request-revalidation`,
GET `/search/deposits?q=&workflow=&after=&limit=`, GET `/dashboard/summary` and
GET `/reports/deposits.csv`. Summary aggregate paise uses a decimal **string** to
preserve exact totals beyond JavaScript's safe integer range. Search is keyset-paginated
by UUID; export is independently capped at 10000 rows and audited. Financial holds have
typed categories and can require EXTERNAL_BODY_NOC; release policy snapshots must match.

Implemented in Phase 1B once its tests pass: POST/GET `/release-cases`, GET
`/release-cases/{id}`, POST `{id}/documents`, `{id}/submit`,
`{id}/clearances/{bureau}/decision`, `{id}/return`, `{id}/holds`,
`{id}/holds/{hold_id}/resolve`, `{id}/approve`, `{id}/issue-document`.
POST/GET `/replacements`, POST `/replacements/{id}/approve`, POST `/monitoring/run`
and GET `/notifications`. Expected versions, idempotency and scope checks apply.

Release evidence is separate from deposit registration evidence and does not invalidate
the accepted registration evaluation. Return-for-correction increments the release
input revision and invalidates prior clearances without deleting their history. Pending
or rejected bureaus and active holds block approval/issuance. Final approver cannot be
maker, prior registration reviewer or any prior clearance actor, even after role changes.
Issuer must be independently scoped to APPROVAL_BUREAU (FDR/RPGF) or COUNCIL (RTGS/ONLINE).
All generated results are SYNTHETIC, carry no financial authority and never mark bank
settlement or deposit RELEASED. TERM_COMPLETED for RTGS/ONLINE checks the calendar ten-year
anniversary from deposited_on; exception reasons require branch evidence and human review.

Case-only role bindings grant only the case and its deposit/evidence, not all institution
records. Current list endpoints are bounded to 100; large reports need cursor pagination.

## Document intelligence contracts (implemented)

Phase 2 adds GET `/deposits/{id}/intelligence`, POST `/documents/{id}/corrections`,
POST `/corrections/{id}/decision`, POST `/discrepancies/{id}/resolve`,
POST `/deposits/{id}/verify-simulated`, POST `/documents/{id}/retry`, and scoped GET
`/documents/{id}/preview/{page}`. Corrections require finite in-page coordinates and
an independent reviewer; current evaluation must be refreshed after confirmation.
Substantive discrepancies cannot be waived while still present in the current evaluation.
Simulation does not change verification authority. Readiness reports queue degradation
without denying safe durable intake. These are implemented; extended production contracts
below remain pending qualification.

Versioned obligations/evaluate, verify (SIMULATED/authorized ports), corrections,
replacement and renewal requests, release-cases/submit, bureau decisions, approve and
issue-document follow baseline action endpoints. No unconstrained PATCH status.
Release requires complete clearances, no holds, independent signatory, fresh evidence,
current policy activation and type-specific issuer; failures must return explainable 409.


## Adopted independent review amendments

Canonical routes use /deposits (supersedes /instruments), and POST /obligations creates the distinct parent. POST /deposits/{id}/correct accepts expected_version and declarations only in DRAFT, increments input_revision and invalidates evaluation. Missing required document keeps DRAFT with an incomplete intake error. Safe substantive FAIL/REVIEW enters PENDING_SCRUTINY; unresolved blockers prevent acceptance. Mutation commands bump version, evaluation never input_revision. Fresh evaluation must match input_revision, current policy_revision and document_set_hash. Multipart request fingerprint hashes bytes + canonical category/metadata, not MIME boundaries. API DB/storage readiness is separate from Redis/worker degradation: intake persists outbox while broker is down. Phase 1B adds release request, scoped clearance, holds, independent approval and SYNTHETIC issuance; no bank instruction.
