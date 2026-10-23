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
| POST /instruments | Institution maker | institution_id, bank_code, reference (transient), amount_paise, issue_date, maturity_date; returns masked FDR DRAFT |
| GET /instruments | Scoped | Bounded list; optional institution_id |
| GET /instruments/{id} | Scoped | FDR with documents, evaluations, review decisions |
| POST /instruments/{id}/documents | Institution maker | multipart PDF <=10 MiB; immutable private object; returns QUARANTINED metadata |
| GET /documents/{id}/content | Scoped | Authenticated streamed PDF attachment only if READY; audited access |
| POST /instruments/{id}/evaluate | Scoped writer | expected_version; stores cited deterministic evaluation; bumps version |
| POST /instruments/{id}/submit | Institution maker | expected_version; READY document + current validation; -> SUBMITTED |
| POST /instruments/{id}/review | Assigned OFFICER | expected_version, decision ACCEPT_REGISTRATION/RETURN, reason >=10 chars; -> ACCEPTED or DRAFT; no bank/release certification |
| GET /audit-events | Scoped | Bounded tenant events; no unscoped financial logging |
| GET /work-queue | OFFICER | Assigned SUBMITTED FDRs |
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
blocks submission/acceptance. Missing document extraction requires human evidence review.

## Later contracts (unimplemented)

Versioned obligations/evaluate, verify (SIMULATED/authorized ports), corrections,
replacement and renewal requests, release-cases/submit, bureau decisions, approve and
issue-document follow baseline action endpoints. No unconstrained PATCH status.
Release requires complete clearances, no holds, independent signatory, fresh evidence,
current policy activation and type-specific issuer; failures must return explainable 409.
