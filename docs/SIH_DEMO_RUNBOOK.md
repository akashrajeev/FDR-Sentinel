# SIH demonstration runbook

## Start and inspect

1. Run `python scripts/bootstrap.py` then `docker compose up --build -d`. Bootstrap
   preserves existing data/credentials and provisions missing local keys. When metadata
   clock skew affects APT, use the explicit recent signed-snapshot build documented in
   README; never disable signature or expiry verification.
2. Portal: http://localhost:8088. Local identity: http://localhost:8081. Independent
   sandbox OpenAPI: http://localhost:8092/docs. Actual captured SMTP inbox:
   http://localhost:8025. All published ports bind loopback. Do not expose this stack publicly.
3. Generated passwords are in ignored `.env`: institution, other-institution, reviewer,
   pgrc, vigilance, approver, issuer, auditor and operator. Convert hyphens to underscores
   in environment names (DEMO_OTHER_INSTITUTION_PASSWORD). Never put passwords in slides.
4. Run `scripts/generate_fixtures.py` in the installed Python environment for clearly
   fictional PDF examples. Root `.local` content, backups and credentials stay out of Git.

## Institution and verification

The initial fictional institution is SYNTHETIC-001. Inspect source examples through
Connected sandbox systems or the authenticated sandbox catalogue. SB-FDR-001 has bank
SYN-BANK, reference ending 0001, 350000000 paise (INR 35 lakh), dates 2016-10-01 and
2026-10-01. SB-FDR-RENEWAL / SB-FDR-HOLD / SB-RTGS-001 illustrate other source records.
These independently stored examples are not real bank instruments. A bank ledger ID is
an explicit source-record locator; matching is limited to the fields in the local contract.

Register matching fictional declarations with the institution account, upload proof,
wait for actual READY scanning/extraction, evaluate and submit. Check the institution
registry from Institutions. As reviewer, request an independent bank check using its
source-record ID. Expand the observed record and compare declared values. Choose delayed
or one-transient-failure transport behavior to show persisted progress/retry. Mismatch,
missing, pending or stale initiated checks do not count as a match or permit acceptance.
Return a deficient deposit, correct it, supersede proof, reevaluate and disposition the
old discrepancy before recording independent acceptance. Originals remain downloadable.

## Operator and CSV

Onboard a new fictional institution as maker. Sign in separately as operator, assign
reviewer/other scoped officers with a reason and expiry. Bureau roles also require
institution/case access. Operator status cannot access financial evidence or approve
cases, and self-grants are prohibited. For new registry examples, the separate sandbox
fixture administrator can POST immutable fictional source records through its API; its
admin key is not given to the portal runtime. This prepares data, not verification outcomes.

Use Legacy import to download the header, preview a UTF-8 synthetic CSV, inspect its
hash/count/paise total, and commit the same file. Invalid rows, duplicate references,
wrong scope or changed preview hash prevent the whole batch from being committed.
Imported entries remain DRAFT and still need evidence, rules and review.

## Maturity, renewal and issuance

Release cases contains the product-policy clock override and reminders. Filter by
deposit ID to inspect 90/30/7-day or matured alerts and actual SMTP delivery status.
Read the matching message in Mailpit. Re-running the same band does not create another
notification. SMTP dead letters can be retried by an assigned reviewer after recovery.

Register and accept a later covering fictional instrument with its proof. The maker
requests renewal/replacement; a different reviewer authorizes it. The old record stays
REPLACED with its lineage and evidence. Renewal does not mean release of funds.

Create a release case for an accepted eligible example, upload request letter,
Affidavit 6 and latest approval proof; accepted deposit proof is also required. Submit
to bureaus. Clear Vigilance and Grants, attempt approval and show PGRC blocking. Clear
PGRC in its own scoped account. A separate approver records the reviewed basis, and a
separate type-authorized issuer generates a synthetic NOC/sanction PDF. Exception orders
and active holds still block this path until explicitly dispositioned with evidence.

Only after issuance may its recorded issuer send a receipt to the AICTE sandbox and
reconcile with an independent bank ledger ID. Show remote request IDs, attempts and
SANDBOX_COMPLETED or rejection. This is actual network/state processing over fictional
records; it never sets real RELEASED, makes bank confirmation or moves real money.

## Repeatable verification

`docker compose --profile test run --rm test` runs the real-service backend suite.
`.venv\Scripts\python scripts/local.py -m pytest -q -m browser` runs the browser suite.
`scripts/fresh_acceptance.py` exports only source files into a new ignored directory,
generates new credentials, builds isolated images, starts fresh portless services,
runs backend network tests and stops only its generated project while retaining evidence.
It never resets current demo volumes. See SIH_ACCEPTANCE.md and STATUS.md for scope/results.
