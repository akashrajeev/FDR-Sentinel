# Implementation plan

SIH completion scope was extended on 2026-10-26: real independent bank/AICTE sandbox
APIs with fictional data, durable source exchanges and reconciliation; actual local
SMTP; operator assignment and transactional CSV; full browser and clean-source/fresh-
volume acceptance. See SIH_COMPLETION_PLAN.md for dependencies and STATUS.md for results.
This work does not wait for production authorization and does not remove production gates.
Phases 5A, 5B and 5C are complete locally; STATUS.md records the 80-test backend,
eight-journey browser and clean-deployment acceptance results. The next milestone is
production activation qualification (Phase 4B), requiring the external inputs listed there.

Baseline reviewed: ARCHITECTURE.md v1.0, AGENT_START_HERE.md and ARCHITECTURE_SLIDE.svg.
Assessment date: 2026-10-23 (Asia/Kolkata). ARCHITECTURE_SLIDE.png was not present.
This plan describes work; STATUS.md is the implementation evidence register.

## Findings and resolved ambiguities

1. The brief asks Phase 1 to include upload and review, whereas baseline Stage 2 owns
   document processing. Move private upload, quarantine, antivirus and digital PDF
   extraction into Phase 1. Advanced OCR/AI remains Phase 2.
2. Baseline Stage 1 includes release, but a small first vertical slice cannot safely
   imply all release controls. Phase 1 ends at registration review. Release endpoints
   do not exist in Phase 1A. The adopted review brings a safe thin lifecycle and synthetic release skeleton into Phase 1B; D6/D7 require that checkpoint.
3. APH 2024-27 regulates online security deposits and historical FDRs. Registering a
   historical FDR is not permission to create a new FDR instead of required online
   payment. Capture obligation context separately. No global ten-year FDR rule.
4. Bank maturity, deposit term and release eligibility are distinct. Dates never
   trigger release. Manual document review never yields BANK_CONFIRMED.
5. Table 1.4 is contextual, not a flat minimum for every institution. Limit the first
   evaluator to new Engineering and Technology UG, explicit ownership/lease factors,
   government/aided exemption and no exceptional history. Unknown cases return REVIEW.
6. Handbook academic-year coverage is known; legal commencement day and amendments
   require policy-owner confirmation. Do not fabricate exact statutory effective dates.
   Model academic applicability and source status explicitly; rules remain provisional.
7. Source retrieval is not proof all current corrigenda were reviewed. Production
   activation is blocked until a policy owner signs off source hash and amendments.
8. Presigned direct upload adds race and CORS complexity to the initial slice. Use
   bounded authenticated multipart upload to private object storage, immutable keys,
   quarantine and asynchronous scanning. This preserves the security invariants.
9. A hash chain alone is not immutable audit. PostgreSQL trigger blocks application
   UPDATE/DELETE; DB-owner attacks require external anchoring/backups in Phase 4.
10. Platform admin provisioning is not institution self-selection of a privileged
    scope. OIDC subject assignments are server controlled; self-onboarding creates
    only the caller's institution membership. First review officers have explicit scopes.
11. No full financial reference in the first slice: store a bank identifier and masked
    last four reference characters; use a keyed digest for duplicate detection. Future
    encrypted full reference needs a key-management/rotation design.
12. Outbox publication can occur twice. Workers lock aggregates and are replay safe;
    never claim exactly-once broker delivery.

## Executable phases

| Phase | Dependencies | Deliverables | Measurable acceptance |
|---|---|---|---|
| 0 Architecture validation | Baseline and official-source research | Eight requested design documents, decision log, source register, backlog | Each requirement mapped to phase/test; threat boundaries and unknowns explicit; Git checkpoint |
| 1 Registration review slice | Phase 0 | FastAPI, PostgreSQL migration, OIDC/PKCE React portal, onboarding, immutable private PDF upload, Redis/Celery scan/extraction, versioned evaluation, officer decision, audit/outbox/idempotency, Compose/CI | Real PostgreSQL tests; tenant isolation; JWT denial; scan fail-closed; replay/stale transitions; browser journey institution to officer; actual results recorded; Git checkpoint |
| 2 Document intelligence | Phase 1 | OCR for image-only PDF, typed extraction/corrections with page/bounds, discrepancy resolution, SIMULATED bank adapter, authorized connector ports | D1/D2/D9 positive and adversarial fixtures; extraction precision/recall on labeled corpus; retry/failure evidence |
| 3 Lifecycle and release | Phases 1-2 | Clock-based reminders, linked replacements, obligations by historical era, release case state machine, scoped bureau clearances, holds, independent final approval, synthetic issuance | D4-D7; PGRC cannot act as Vigilance; no pending/held case can issue; RTGS/FDR branches; notifications dedupe |
| 4A Local operational qualification | Phases 1-3 | Restricted DB/environment/container runtime, optional verified-MFA gate, trace propagation/export, security/dependency checks, outage/load/restore scripts and runbook | Passing actual-service suite/browser workflows; correlated broker trace; measured read load and isolated restore; recorded advisory limitations; Git checkpoint |
| 4B Production activation (blocked) | 4A plus sponsor/authorized owners | Approved policy source/amendments, actual IdP/MFA, managed encryption/keys, authorized external contracts, retention/deletion and external immutable audit/PITR, independent security assessment | Written scope/authority, qualified MFA/recovery/retention/restore/operational objectives and all current security findings reviewed; separate reviewed implementation before removing startup gate |

## Phase 1 task order

1. Lock Python/Node dependencies; configure Compose/PostgreSQL/Redis/Keycloak/private S3/ClamAV (SeaweedFS adopted in ADR-021).
2. Alembic schema with constraints, scoped identity, audit trigger, idempotency records.
3. OIDC JWT verification and server-owned role/scope lookup; provisioning/seed tooling.
4. Onboarding and FDR services; integer paise, date constraints, unique reference digest.
5. Upload -> quarantine -> outbox -> scan -> digital extraction, retriable failure states.
6. Pure rules evaluate context and evidence; freeze inputs/source/rule hashes.
7. Safe submission -> PENDING_SCRUTINY even with substantive FAIL -> officer return/correction or blocker-free registration acceptance; version checks and maker/checker.
8. React typed API forms, polling document results, review/evidence/audit timeline.
9. Integration/security/worker tests, frontend build, Compose/browser smoke, status and Git.

## Clarifications deferred without blocking local development

Policy owner: authoritative APH amendments, exact effective dates, old deposit eras,
exemptions, lease categories, crediting existing deposits and release signatories.
Sponsor: authorized bureaus and scope, approved IdP/MFA, storage region, retention,
incident response, institution identity proof, lawful AI data processing, bank contracts.
These block production activation or later phases, not synthetic local development.

No infrastructure split beyond API/web/worker and required dependencies. Use one Beat
scheduler. Production deployment is a later reviewed milestone; local success is not
production suitability or regulatory certification.


## Adopted independent review amendments

Adopt independent review P0.1-P1.6 (user-supplied review date 2026-10-24; task date 2026-10-23). No code or migrations existed, so no migration impact. Track A: Phase 1A safe deposit intake/scrutiny; Phase 1B thin maturity, replacement lineage, PGRC/Vigilance blocking, independent sign-off and SYNTHETIC output. Bring these Phase 3 tasks forward without relaxing controls. Track B: Phase 2 OCR/AI, SIMULATED adapters, extended conditions and hardening. E1-E8 are added acceptance obligations; full production qualification remains Phase 4.
