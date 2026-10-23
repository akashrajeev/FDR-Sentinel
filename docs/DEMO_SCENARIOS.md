# Demo scenarios

All identities, institutions, FDRs and PDFs are synthetic. No bank verification, AICTE
registry connection, legal approval, NOC or money movement exists in Phase 1.

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

Fixture text format includes labeled `Amount paise`, `Issue date`, `Maturity date` and
synthetic institution identifier. Extraction is a deterministic digital-text parser in
Phase 1; scanned/OCR and optional AI assistance are later work, never falsely advertised.

## Later judging scenario

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
NOC/sanction. This scenario is planned until all corresponding tests exist and pass.

Deliberate outages: scanner offline -> document unavailable, no submission; Redis offline
-> persisted outbox, eventual retry; duplicate worker -> no duplicated decision/evidence.
Reset only via explicit dedicated demo/test database tooling, never manual production SQL.


## Adopted independent review amendments

Bring full lifecycle skeleton forward to Phase 1B. Deficient deposit reaches scrutiny, receives correction request, corrects and reevaluates before acceptance. RTGS/ONLINE can be registered without maturity dates. A synthetic matured legacy FDR still cannot issue while PGRC pending. Vigilance, other applicable clearances, independent approval and no holds are required. CLOSURE/MERGER/CONVERSION/OTHER reasons require extra evidence and policy review; they cannot use a maturity-only shortcut. Show all output as SYNTHETIC; never bank-confirmed or paid.
