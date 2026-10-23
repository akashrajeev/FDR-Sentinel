# API contracts

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
| POST /deposits | Institution maker | institution_id, bank_code, reference (transient), amount_paise, issue_date, maturity_date; returns masked typed deposit DRAFT (FDR dates required; RTGS/ONLINE dates optional) |
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

## Later contracts (unimplemented)

Versioned obligations/evaluate, verify (SIMULATED/authorized ports), corrections,
replacement and renewal requests, release-cases/submit, bureau decisions, approve and
issue-document follow baseline action endpoints. No unconstrained PATCH status.
Release requires complete clearances, no holds, independent signatory, fresh evidence,
current policy activation and type-specific issuer; failures must return explainable 409.


## Adopted independent review amendments

Canonical routes use /deposits (supersedes /instruments), and POST /obligations creates the distinct parent. POST /deposits/{id}/correct accepts expected_version and declarations only in DRAFT, increments input_revision and invalidates evaluation. Missing required document keeps DRAFT with an incomplete intake error. Safe substantive FAIL/REVIEW enters PENDING_SCRUTINY; unresolved blockers prevent acceptance. Mutation commands bump version, evaluation never input_revision. Fresh evaluation must match input_revision, current policy_revision and document_set_hash. Multipart request fingerprint hashes bytes + canonical category/metadata, not MIME boundaries. API DB/storage readiness is separate from Redis/worker degradation: intake persists outbox while broker is down. Phase 1B adds release request, scoped clearance, holds, independent approval and SYNTHETIC issuance; no bank instruction.
