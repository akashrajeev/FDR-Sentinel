# SIH functional acceptance

Target: real application, persistent services and network protocols; fictional records
and explicitly named sandbox institutions. No real bank/AICTE authority or funds movement.
Exact executed results are in STATUS.md. Listed tests are evidence only when their run passes.

| Scenario | Browser evidence | Additional actual-service/API evidence |
|---|---|---|
| D1 Registration/document review | real_pkce_and_worker_to_officer; new_onboarding_operator_assignment_registry_and_csv | PostgreSQL intake, private objects, scanner and outbox tests |
| D2 Discrepancy/correction | deficient_scrutiny_return_correction_and_tenant_isolation; scanned_evidence_annotation_and_simulated_bank (name retained, uses real independent sandbox) | Evidence revision/hash, independent transcription, conflicting-source tests |
| D3 Deterministic contextual rules | deficient submission is accepted for scrutiny but acceptance is denied until corrected; visible provisional citations | Rules/API fixtures cover UG base, private-lease factor, exemptions, unknown/aggregate review |
| D4 Maturity/reminders | maturity_email_and_independent_renewal_lineage: injected date and actual SMTP SENT | Clock/dedupe tests, actual Mailpit content and failure/dead-letter/retry |
| D5 Renewal/replacement | independent renewal authorization retains original as REPLACED | Scope, chronology, principal and immutable-lineage gates |
| D6 Pending clearance block | pgrc_block_to_independent_synthetic_issuance: approval attempt denied while PGRC pending | Cross-bureau denial and financial/exception holds |
| D7 Human issuance/reconciliation | Same browser journey issues PDF, receives AICTE sandbox receipt and bank SANDBOX_COMPLETED | Real HTTP reconciliation only after independently human-issued output; actual RELEASED prohibited |
| D8 Access/replay | Different institution cannot see corrected record; lost-response retries keep identities | JWT/tenant/bureau/maker-checker, runtime DB privileges, signed-source replay/correlation |
| D9 Source distinction | Bank check queries independent fictional ledger; actual mismatch with transient HTTP failure and retry | Independent data comparison; original declarations/source/decisions remain separate |
| D10 Observable failure/recovery | Waiting/attempt/outcome UI on real bank exchange; visible SMTP delivery | Actual refused SMTP transport through dead letter and recovery; source HTTP 503 and signature/stale-result tests; existing Redis/ClamAV drills |

Additional acceptance: operator grants/revocations require explicit valid scope and reason,
CSV preview/commit is atomic and DRAFT-only, and a clean source export boots in isolated
fresh volumes with new generated credentials and runs the full backend network suite.
The cold backend suite and the live browser suite are distinct evidence; neither is
represented as a hosted CI run. No Git remote is configured in this workspace.

The portal's mature software modules are not replaced by canned success responses.
Authentication, DB transactions, file storage/scanning, OCR, policy evaluation, roles,
human decisions, audit, source HTTP, SMTP and reconciliation code actually execute.
The old echo-only fixture endpoint remains solely for historical/regression compatibility;
its interactive success controls have been removed from the presentation UI.
