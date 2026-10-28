# Judge guide

## The project in one minute

FDR Sentinel is a role-scoped workspace for institutional security deposits. It connects
an institution's declaration to original proof, provisional evaluation, independent source
checks, officer scrutiny and later lifecycle actions. A reviewer can see why a record is
blocked and what evidence supports the next decision, without treating a machine result
as financial or regulatory authority.

The target is SIH26265. The repository's requirement map uses the linked public mirror as
a discovery baseline, not an official sponsor acceptance certificate. The project
complements existing online AICTE application processes.

## What is different about the design

- **Evidence before status.** Original PDFs, hashes, extracted fields, page evidence,
  superseding revisions and discrepancy decisions remain linked.
- **Independent decisions.** Maker, reviewer, bureau, approver and issuer actions are
  separated by identity and scope. A sandbox response cannot approve a release.
- **Follow-through beyond intake.** Maturity, replacement lineage, clearance holds,
  notification retries, intervention episodes and audited exports remain part of the case.
- **Failure is visible.** Quarantine, processing failures, pending source exchanges,
  retries and dead letters are states to inspect, not hidden success animations.

These are product design choices. Novelty, legal acceptance and real-world impact have
not been established by a sponsor evaluation or representative human pilot.

## A useful demonstration order

Use the **local stack** to demonstrate execution. The public browser demo is a separate
simulation for exploring the interface and must be labeled as such.

| Step | What to show | What to say accurately |
|---|---|---|
| 1. Intake | Institution context, obligation, declaration and uploaded fictional proof | Amounts and documents are synthetic |
| 2. Evidence | Actual scanning to READY, extracted values and original/page view | READY is processing readiness, not authenticity |
| 3. Scrutiny | A deficient case returned, correction and a different officer's decision | Registration acceptance is a human decision, not release |
| 4. Source exchange | Request/attempts/result against a separate fictional ledger | A match covers the local contract's fields only |
| 5. Maturity | Disclosed synthetic date, reminder and actual Mailpit message | Email SENT alone is not proof of inbox receipt |
| 6. Replacement | Covering later record, independent authorization and retained lineage | The prior record is retained; no funds released |
| 7. Release | Missing PGRC blocks approval, then scoped clearances, separate approval/issuer | Synthetic NOC/sanction is not settlement |
| 8. Follow-up | Scoped report, intervention acknowledgement, source resolution and CSV | Acknowledgement does not waive the unresolved source fact |
| 9. Administration | New-institution scope assignment and legacy CSV preview/commit | Operator cannot self-grant or make financial decisions; imports stay DRAFT |

The [runbook](SIH_DEMO_RUNBOOK.md) has exact actions. These are demonstration targets,
not a claim that all scenes have been captured in the latest video. The acceptance map
names relevant tests; only a recorded passing execution is test evidence.

## Architecture explanation

See the shared [architecture diagram in the README](../README.md#architecture).

The web workspace authenticates through Keycloak and sends commands to FastAPI.
PostgreSQL stores authoritative state, audit and the outbox. Original PDFs live in private
S3-compatible storage. Redis/Celery dispatch background scanning, extraction and source
work. Provisional deterministic evaluation supports independent human scrutiny. Lifecycle
operations reuse the same evidence, access and audit boundaries.

The image is an implementation overview, not proof of production controls or official
integration. [ARCHITECTURE.md](../ARCHITECTURE.md) maps it to actual source files.

## Evidence and measurements

The historical status register records local backend/browser checks and fresh isolated
qualification. The current hosted CI run is failed, not green; see
[verification](VERIFICATION.md) for its read-only Ruff-cache failure and proposed fix.
Later browser/security-audit steps were skipped in that run.

Two small measurements are useful if their limits stay attached:

- Extraction used **16 expected fields across four generated same-layout variants**,
  including one scan. Repeating those inputs 48 times does not create 48 independent
  samples. This is not representative bank-document accuracy or authenticity testing.
- An eight-case controlled intervention-report comparison used **16 versus 1 HTTP GET
  reads**. It was a scripted per-record inspection proxy versus a consolidated report,
  not a human/manual register baseline, SQL-query reduction or production load test.

Do not infer human hours saved, fraud detection rates, production throughput, legal
compliance, bank authenticity or monetary savings from these exercises. Historical exact
commands/results are retained in [MEASUREMENTS.md](MEASUREMENTS.md).

## Honest answers to likely questions

**Is it integrated with real banks or AICTE?** No. The network adapter runs against an
independent persistent fictional sandbox with signed exchanges and retry/reconciliation
states. Official contracts, written authority and an authorized test environment are open.

**Does AI approve anything?** No. Optional local AI proposes evidence-linked fields.
Independent confirmation and deterministic rules govern use. It is disabled by default;
the current recording has not established an AI result or an accuracy improvement.

**Are the rules complete and legally approved?** No. The APH 2024-27 fixtures are versioned,
cited and provisional. Unknown/aggregate contexts go to human review. Current amendments,
historical applicability and exceptions require authorized policy-owner review.

**Does a synthetic NOC release money?** No. It demonstrates a controlled workflow and
output generation. It does not mark real settlement or confer financial authority.

**What remains before deployment?** Representative authorized documents and pilot data,
policy/integration authority, strong real identity assurance, TLS, approved encryption and
key management, retention, independent security review, production recovery and operating
ownership. The [coverage map](PROBLEM_STATEMENT_COVERAGE.md) lists acceptance gaps.
