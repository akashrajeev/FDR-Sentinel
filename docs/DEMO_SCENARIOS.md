# Demo scenarios

All identities, institutions, FDRs and PDFs are synthetic. The implemented independent
bank/AICTE sandbox APIs use persistent fictional ledgers and registry records. No real
bank verification, official AICTE registry connection, legal approval or money movement
is claimed. Issued sample
NOC/sanction PDFs are visibly synthetic and carry no authority.

The current complete judging sequence, including operator assignment, CSV intake,
actual SMTP delivery, source checks and sandbox release reconciliation, is in
`SIH_DEMO_RUNBOOK.md`. D1–D10 evidence is mapped in `SIH_ACCEPTANCE.md`; `STATUS.md`
records actual executed results. The older scenarios below retain milestone context;
their SIMULATED echo checks are historical regression fixtures, not the current live
source API demonstration.

## First complete slice

1. Start local stack and generate ignored credentials. Login as synthetic institution
   using Keycloak. Onboard a declared institution; registry banner says unverified.
2. Register synthetic FDR with amount in rupees converted to integer paise, bank code,
   reference and issue/maturity dates. Only masked reference returns from API.
3. Upload fixture PDF. Observe QUARANTINED then READY after actual antivirus scan and
   digital text extraction. Inspect document hash, scan method and page-linked evidence.
4. Evaluate: supported UG context shows cited 35-lakh base; a private-lease context
   shows 70 lakh. Provisional-policy warning remains. Underfunded instrument enters scrutiny with FAIL and cannot be accepted;
   unknown legal context requires human review. No outcome says legally compliant.
5. Submit a funded record. Switch to assigned officer, inspect evidence and evaluation,
   return with a reason, then resubmit and accept registration. Observe version changes
   and immutable actor/time audit. MANUALLY_REVIEWED is visible, no bank-confirmed claim.
6. Login as different institution: record and document unavailable. Replay an API key:
   same response, one event. Stale version rejected. Worker cannot approve anything.

Generate varied digital/scanned synthetic PDFs with `scripts/generate_fixtures.py`.
The original labeled-paise fixture remains a regression case; the worker also parses
INR layouts and runs real Tesseract OCR. Optional local AI proposes source-linked values
without changing declarations, policy decisions or approval authority.

## Complete lifecycle judging scenario (implemented and browser-tested)

Phase 1B brings the deterministic PGRC-blocked release skeleton forward: use the Release
cases tab, upload scanned request/Affidavit/approval evidence, submit, record Vigilance
and Grants clearance, attempt approval as `approver` and observe PGRC PENDING. Clear PGRC
as `pgrc`; approve independently as `approver`; issue a visibly synthetic NOC as `issuer`.
RTGS uses a ten-year deposited_on anniversary and a synthetic sanction-order branch.
The `reviewer` account is also explicitly bound to the GRANTS bureau for the local demo;
it cannot perform final approval. All scopes are server controlled.

D2 evidence mismatch -> correction; D9 SIMULATED bank source; D4 maturity warning;
D5 replacement with retained original; D6 attempted release blocked by PGRC; D7 scoped
PGRC and Vigilance clearance then competent independent approval and SYNTHETIC draft
NOC/sanction. Matching API/browser tests now exist and pass; see STATUS.md for exact runs.

Deliberate outages: scanner offline -> document unavailable, no submission; Redis offline
-> persisted outbox, eventual retry; duplicate worker -> no duplicated decision/evidence.
Reset only via explicit dedicated demo/test database tooling, never manual production SQL.

## Evidence adjudication and reporting (implemented)

Upload the scanned synthetic fixture, wait for actual READY processing and open the
protected page preview. Select the amount region, propose a typed transcription as the
maker, submit for scrutiny, and confirm as an independent reviewer. Run a fresh policy
evaluation. A current substantive mismatch cannot be waived through discrepancy
disposition. Run the SIMULATED mismatch scenario and show that verification remains
institution-declared. Show the current provisional source/citation and retained original.

Open Reports as a scoped officer. Compare complete-scope counts against the bounded
operational list, search institution/ID/last four and download an audited safe CSV.
Synthetic case durations show their sample count and automated basis; no impact savings
or authentic institutional financial data is claimed. For a newly onboarded institution,
provision reviewer scope through the operator CLI before expecting it in that queue.

The automated transport-recovery scenario drops the network response after the real
server commits both a deposit and upload. Retried keys return the same identities and
one READY document. Run service outage drills separately from the browser demonstration.


## Adopted independent review amendments

Bring full lifecycle skeleton forward to Phase 1B. Deficient deposit reaches scrutiny, receives correction request, corrects and reevaluates before acceptance. RTGS/ONLINE can be registered without maturity dates. A synthetic matured legacy FDR still cannot issue while PGRC pending. Vigilance, other applicable clearances, independent approval and no holds are required. CLOSURE/MERGER/CONVERSION/OTHER reasons require extra evidence and policy review; they cannot use a maturity-only shortcut. Show all output as SYNTHETIC; never bank-confirmed or paid.
