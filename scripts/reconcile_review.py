"""One-time non-destructive reconciliation before the first schema exists."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
changes = {
    'DATABASE_DESIGN.md': [
        ('enabled flag, role INSTITUTION/OFFICER/AUDITOR; no passwords', 'enabled flag; no global role and no passwords'),
        ('| assignments | Principal + institution unique; officer read/review only in assigned institutions; no wildcard role claim |', '| role_bindings | Principal, role, scope_type INSTITUTION/BUREAU/CASE, scope_id, enabled, validity; multiple scopes; operator-provisioned privileges |\n| security_deposit_obligations | Institution FK, regulatory_event, context, policy snapshot, independent obligation status |'),
        ('| instruments |', '| deposit_records |'),
        ('maturity > issue, workflow/verification/lifecycle separated, version >=1, maker', 'type FDR/RPGF/RTGS/ONLINE/OTHER_LEGACY; FDR dates required, others optional; obligation FK; separate workflow/verification/lifecycle, command version and input_revision, maker'),
        ('Returns move back to DRAFT; missing/replacement documents can be uploaded with a new key.', 'Returns move back to DRAFT. Explicit correction changes input_revision. New immutable documents invalidate evaluation. Evaluation stores input_revision, policy_revision, document_set_hash and evaluated_at; evaluation does not change input_revision.'),
    ],
    'API_CONTRACTS.md': [
        ('FDR DRAFT', 'typed deposit DRAFT (FDR dates required; RTGS/ONLINE dates optional)'),
        ('-> SUBMITTED', '-> PENDING_SCRUTINY even with substantive FAIL/REVIEW'),
        ('known FAIL\nblocks submission/acceptance', 'known FAIL\nblocks acceptance, while safe deficient records may enter scrutiny'),
        ('Assigned SUBMITTED FDRs', 'Assigned PENDING_SCRUTINY deposits'),
        ('`/instruments', '`/deposits'),
        (' /instruments', ' /deposits'),
    ],
    'IMPLEMENTATION_PLAN.md': [
        ('do not exist until Phase 3. D6/D7 are not claimed by Phase 1.', 'do not exist in Phase 1A. The adopted review brings a safe thin lifecycle and synthetic release skeleton into Phase 1B; D6/D7 require that checkpoint.'),
        ('Submit -> officer return or accept registration', 'Safe submission -> PENDING_SCRUTINY even with substantive FAIL -> officer return/correction or blocker-free registration acceptance'),
    ],
    'DEMO_SCENARIOS.md': [
        ('Underfunded instrument fails;', 'Underfunded instrument enters scrutiny with FAIL and cannot be accepted;'),
    ],
}
annex = {
 'IMPLEMENTATION_PLAN.md': '''Adopt independent review P0.1-P1.6 (user-supplied review date 2026-10-24; task date 2026-10-23). No code or migrations existed, so no migration impact. Track A: Phase 1A safe deposit intake/scrutiny; Phase 1B thin maturity, replacement lineage, PGRC/Vigilance blocking, independent sign-off and SYNTHETIC output. Bring these Phase 3 tasks forward without relaxing controls. Track B: Phase 2 OCR/AI, SIMULATED adapters, extended conditions and hardening. E1-E8 are added acceptance obligations; full production qualification remains Phase 4.''',
 'DATABASE_DESIGN.md': '''Separate obligations from deposit_records now. Deposit type is FDR/RPGF/RTGS/ONLINE/OTHER_LEGACY; online records have no invented maturity. Identity roles live only in many scoped role_bindings with enabled and validity dates, not principals.role. Scope types INSTITUTION/BUREAU/CASE are reserved; bureau decision authority also requires case/institution assignment. Phase 1B brings release_cases, clearances, holds, lineage and notifications forward. Evaluation freshness is (input_revision, policy_revision, document_set_hash); command version is distinct. Multipart fingerprints use verified bytes SHA and category; stable response/object IDs on replay. Unreferenced private objects need grace-period reconciliation. HMAC key version is stored; eventual managed-key encrypted canonical references require authorized reconciliation, redacted access and dual-key rotation.''',
 'API_CONTRACTS.md': '''Canonical routes use /deposits (supersedes /instruments), and POST /obligations creates the distinct parent. POST /deposits/{id}/correct accepts expected_version and declarations only in DRAFT, increments input_revision and invalidates evaluation. Missing required document keeps DRAFT with an incomplete intake error. Safe substantive FAIL/REVIEW enters PENDING_SCRUTINY; unresolved blockers prevent acceptance. Mutation commands bump version, evaluation never input_revision. Fresh evaluation must match input_revision, current policy_revision and document_set_hash. Multipart request fingerprint hashes bytes + canonical category/metadata, not MIME boundaries. API DB/storage readiness is separate from Redis/worker degradation: intake persists outbox while broker is down. Phase 1B adds release request, scoped clearance, holds, independent approval and SYNTHETIC issuance; no bank instruction.''',
 'SECURITY_MODEL.md': '''No single global role: identities have many role_bindings (principal, role, scope_type, scope_id, enabled, valid_from/until). Institution self-service grants only own institution maker scope, never bureau/officer. PGRC cannot decide Vigilance; each bureau decision also needs case/institution scope. Maker/checker and independent signatory compare permanent subjects even if roles change. Readiness allows durable intake during broker outage and reports degraded processing. Scanner outage never permits read/approval. Fake bank source remains SIMULATED, never BANK_CONFIRMED.''',
 'TEST_STRATEGY.md': '''Add E1 deficient submission/return/correction; E2 RTGS/ONLINE without maturity; E3 new document invalidates prior evaluation; E4 PGRC/Vigilance and independent final signatory gate SYNTHETIC issuance; E5 closure/merger/conversion evidence and holds; E6 simultaneous stale commands only one succeeds; E7 Redis/ClamAV outage truthfully degraded, no unsafe read; E8 extraction sample size/precision/recall and measured workflow durations. Use realistic synthetic PDFs and separate truth labels; no fabricated impact baseline.''',
 'DEMO_SCENARIOS.md': '''Bring full lifecycle skeleton forward to Phase 1B. Deficient deposit reaches scrutiny, receives correction request, corrects and reevaluates before acceptance. RTGS/ONLINE can be registered without maturity dates. A synthetic matured legacy FDR still cannot issue while PGRC pending. Vigilance, other applicable clearances, independent approval and no holds are required. CLOSURE/MERGER/CONVERSION/OTHER reasons require extra evidence and policy review; they cannot use a maturity-only shortcut. Show all output as SYNTHETIC; never bank-confirmed or paid.''',
 'REQUIREMENTS_MATRIX.md': '''Review acceptance mapping: E1 scrutiny/correction (1A), E2 obligation + typed records (1A), E3 revision/document-set invariants (1A), E4 PGRC-blocked lifecycle browser/API (1B), E5 typed reasons and evidence/holds (1B/extended 3), E6 concurrency and permanent subject separation (1A/1B), E7 degraded queue/scan states (1A/2), E8 realistic fixture measurements (2/4). D4-D7 thin skeleton moves to 1B; full historical/regulatory coverage remains 3. No phase is complete solely because its design is documented.''',
 'ARCHITECTURE_DECISIONS.md': '''ADR-013: distinct security_deposit_obligations and typed deposit_records before migration; avoid FDR-only parent model. ADR-014: PENDING_SCRUTINY accepts safe substantive failures, acceptance remains blocked; incomplete mandatory evidence stays DRAFT. ADR-015: many valid role_bindings by institution/bureau/case, no global role; permanent subject separation. ADR-016: input_revision independent of command version; policy_revision + document_set_hash required for freshness. ADR-017: lifecycle skeleton moved to Phase 1B, then extend intelligence/hardening; no bypass for demonstration. ADR-018: API supports degraded intake with durable outbox during broker outage. ADR-019: canonical full financial references deferred to managed-key encryption; HMAC version explicit. ADR-020: release reasons TERM_COMPLETED/CLOSURE/MERGER/CONVERSION/OTHER have branch evidence/holds, not generic maturity eligibility.''',
}
for name, additions in annex.items():
    path = root / 'docs' / name
    content = path.read_text(encoding='utf-8')
    for old, new in changes.get(name, []):
        content = content.replace(old, new)
    path.write_text(content + '\n\n## Adopted independent review amendments\n\n' + additions + '\n', encoding='utf-8')
