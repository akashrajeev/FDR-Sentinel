# Detailed problem-statement coverage

Scope: a functional SIH system using fictional records and real local services. The
published mirror linked in ARCHITECTURE.md is the discovery baseline, not an official
sponsor acceptance certificate. STATUS.md is the record of executed evidence.
Phase 6 verification: 88 backend tests and nine browser journeys passed, along with
frontend build, fresh isolated deployment and local recovery. These counts establish
the documented synthetic scope, not official sponsor acceptance or legal certification.

## Software gap-closure milestone

| Detailed requirement | Implementation / verification anchor |
|---|---|
| Pending verification and inconsistent independent sources | Durable integration requests; PENDING_VERIFICATION includes pending, stale, failed and conflicting latest source checks |
| Missing or unusable evidence | MISSING_DOCUMENTS tracks absence of active READY proof and required release/exception evidence; quarantined documents do not satisfy it |
| Overdue scrutiny and unresolved discrepancies | OFFICER_REVIEW ages from latest submission/revalidation audit; UNRESOLVED_DISCREPANCY ages from original finding |
| Pending bureau clearances and holds | Current input revision and independent bureau tasks; active financial/legal/exception holds remain blocking |
| Configurable reminders and escalation | Append-only per-institution product policy, actual SMTP reminder and independent supervisor escalation, episode/recipient/stage deduplication |
| Intervention reports | Filtered/paginated full-scope counts, source IDs/findings, acknowledgement, retained resolved history, audited safe CSV |
| Unknown policy contexts | REGULATORY_REVIEW retains citation/evaluation references; financial policy coverage is never silently widened |
| Demonstrable improvement | benchmark_workflow.py compares actual HTTP per-record scripted inspection against consolidated reporting with fixed independent synthetic labels; latency/read-count/accuracy measured |

Deadlines are **product SLAs, not statutory deadlines**. Celery scans every 60 seconds;
manual scoped scans use the same service. Acknowledgement records responsibility but
cannot resolve source facts or grant approval. Resolved episodes remain immutable;
recurrence opens a new episode. Supervisor membership must already exist, and policy
editing grants no permission. An unassigned/revoked supervisor receives no new escalation.
Queued operational email is cancelled after source resolution or access revocation.

Maturity thresholds are configurable; the existing dashboard's "within 90 days" statistic
remains an explicitly fixed reporting window. Sandbox completion retires only fictional
maturity follow-up and does not change the prohibition on real RELEASED.

## What implementation cannot certify

| Acceptance item | Existing behavior / remaining evidence | Responsible input |
|---|---|---|
| Every applicable regulation and amendment | Versioned cited provisional rules, unsupported review, type-specific release branches and holds; full legal applicability cannot be invented | Authorized policy owner confirms sources, effective dates and historical treatment |
| Authorized bank/regulator services | Persistent sandbox with assumed local protocol, signed HTTP, retries and reconciliation | Written authority, official contracts, credentials and authorized test environment |
| Real identities | Synthetic OIDC, scoped provisioning and optional verified-MFA gate | Sponsor onboarding/IdP/MFA policy and assurance testing |
| Production confidentiality/operations | Private objects, restricted runtime, audit and local recovery; local HTTP/storage are development only | Approved TLS, storage encryption/KMS, rotation, retention, external audit, PITR/offsite recovery and incident ownership |
| Security qualification | Automated abuse/race tests and dependency review; recorded OS/JDK findings remain open | Independent assessment and remediation/risk acceptance |
| Real-world impact | Synthetic extraction and controlled proxy; no human baseline or invented savings | Consented representative human pilot and authorized document corpus |
| Hosted CI | Workflow and local suites/fresh deployment | Configured remote/runner and an actual successful run |

These acceptance items remain open. Mocking a signature, authorization, human baseline
or security approval would not close them. They do not block the synthetic SIH flows.
