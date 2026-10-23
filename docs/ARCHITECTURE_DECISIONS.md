# Architecture decisions

ADR-031: local runtime is a separate PostgreSQL role, read-only application filesystem,
temporary bounded scratch space and explicit application-only environment. Migration
owner, IdP admin and demo-user passwords are not inherited by runtime containers.
No DDL, delete, privileged role assignment or history rewrite grants exist at runtime.

ADR-032: trace context is persisted with transactional outbox and forwarded in Celery
headers. Explicit payload-free OTel spans export JSON locally and optionally OTLP.
Native FastAPI automatic tracing is disabled because it records URL query values.
No baggage/SQL/document/token capture is enabled. Remote OTLP remains unexercised.
Reference: https://opentelemetry.io/docs/languages/python/instrumentation/ .

ADR-033: synthetic local approval/issuance can optionally require recent signed IdP
MFA claims. This application gate cannot establish that an IdP really performed MFA;
production enrollment, step-up, mapping and recovery need separate qualification.
The demo exemption is explicit; all production startup remains gated.

ADR-034: distinguish completed local engineering qualification (4A) from production
activation (4B). Sponsor-owned regulatory facts, real connectors, retention/legal
authority, independent assessment and managed infrastructure cannot be fabricated.
Restore targets and load fixtures are isolated; no automatic evidence deletion exists.

ADR-035: browser mutation retry preserves the same key across transport failures and
unknown 5xx outcomes, with a memory-only operation/body fingerprint. A real-API browser
test drops a response after commit and requires the replay to return the same identity
for both JSON deposit intake and multipart document upload. Long search queries no
longer implicitly match the last four characters of unrelated references; wildcards
are literal.

ADR-036: update Keycloak to 26.8.1 using a copied development volume with preserved
original/archive for rollback. Use current Python Debian Trixie base and current pinned
pip. APT must fail on any repository-update error; no signature/expiry bypass is
permitted. Optional recent Debian snapshot build argument handles repository/VM clock
skew while preserving verification; snapshots need deliberate security refresh.
References: https://www.keycloak.org/downloads and https://snapshot.debian.org/ .

ADR-027: programme/level amounts are in a new immutable-version policy fixture; unknown
history and aggregate coverage require review. Single-record amount checks do not assert
that multiple records fulfill an obligation. Legal dates/amendments remain unapproved.

ADR-028: explicit revalidation preserves historical reviews while resetting pending
release scrutiny/clearances. A release case pins its policy revision; policy drift blocks
approval/issuance. Issued synthetic outputs stay historical and never imply settlement.

ADR-029: report totals are computed in PostgreSQL over the full authorized scope, not
the 100-row operational list. Aggregate paise totals are decimal strings for exact client
transport; per-record amounts remain bounded integer paise. CSV cells escape formula
prefixes, export is scoped/audited/capped at 10000 rows, search uses bounded keyset paging.

ADR-030: financial-embezzlement holds require a separately scanned EXTERNAL_BODY_NOC
category and human disposition; ordinary deposit proof cannot lift them. Source authenticity
remains manual/unconfirmed without an authorized external integration.

ADR-022: local Ollama is optional, synthetic-only, schema constrained and host allowlisted.
Model values must independently match deterministic page evidence; quote relinking is
explicit. Proposals are advisory and never change financial or regulatory authority.
Reference: https://docs.ollama.com/capabilities/structured-outputs .

ADR-023: preserve raw extraction and immutable originals; human corrections are bounded
page annotations proposed by one actor and confirmed by an independent reviewer. Confirmed
interpretations enter evaluation snapshots; substantive discrepancies need an explicit
officer disposition after fresh evaluation no longer contains the blocker.

ADR-024: readiness gates DB/storage while processing degradation separately reports
broker, recent worker heartbeat and scanner connectivity. Durable intake remains available.
After five processor failures an event is dead-lettered until scoped officer retry.

ADR-025: Nginx resolves the API service through Docker DNS at runtime, avoiding stale
upstream addresses after container recreation. Actual gateway smoke caught this issue.

ADR-026: new nonnullable processing metadata/counters retain safe server defaults for
compatibility with older API/worker instances during migrations. Local authority check
constraints prohibit BANK_CONFIRMED and RELEASED until authorized integrations and a
separate production qualification change explicitly introduce those states.

ADR-021 (implementation discovery): local MinIO images are no longer publicly pullable
from Docker Hub or Quay in this environment. Its official repository is archived. Use
maintained S3-compatible SeaweedFS 4.48 for local protected object storage, retaining the
S3 port/adapter boundary. This changes a replaceable local dependency, not the required
private object-storage architecture. Sources: https://github.com/minio/minio and
https://github.com/seaweedfs/seaweedfs. Tag 4.48 availability verified against Docker Hub.

| ADR | Decision | Reason / consequence |
|---|---|---|
| 001 | Modular monolith + Celery worker, one PostgreSQL | Required baseline; avoids distributed financial state |
| 002 | Keycloak OIDC RS256 and browser PKCE | No homegrown token issuance; server assignments remain authoritative |
| 003 | Authenticated multipart upload in Phase 1 | Bounded bytes and simpler quarantine authorization; presigned intentions later if needed |
| 004 | Registration acceptance distinct from release | Safe vertical slice, no partial release authority |
| 005 | Narrow provisional APH rule fixture | Academic-year applicability known; amendments/legal dates need owner review |
| 006 | Integer INR paise, keyed reference digest, last4 | Exact money and duplicate control without storing full financial reference |
| 007 | Locked transactions + persistent idempotency + outbox | At-least-once broker safety, atomic workflow/evidence/audit |
| 008 | Immutable private objects, scan fail-closed | Worker failure never permits document consumption or silent approval |
| 009 | Pure deterministic parser/rules first | AI/OCR can be added with evidence; no LLM in decision authority |
| 010 | Phase-based telemetry | JSON request logs, request IDs, metrics/readiness first; OTel collectors/Grafana after workflows |
| 011 | Server scope provisioning, declared onboarding | Self-onboarding never verifies AICTE registration or grants officer role |
| 012 | Separate owner migration/runtime roles for production | Local DB owner is not proof of production tamper resistance |

## Official source register

Primary: [AICTE APH 2024-25 to 2026-27](https://www.aicte.gov.in/sites/default/files/APH%20Final.pdf).
Checked 2026-10-23; URL was accessible via indexed official PDF, with intermittent 502
on subsequent retrieval. Cover identifies academic years 2024-25 through 2026-27.
Clause 1.12/Table 1.4: scoped deposit amounts, exemptions and lease considerations.
Clause 6.46: release evidence, clearances and authorized issuance. Applicable amendments
are not yet exhaustively verified. These fixtures are not a legal-compliance certification.

Policy package must retain source URL, edition, clause/page, source hash when downloaded,
academic applicability, unknown legal commencement date, fixture status, rule checksum
and extraction algorithm version. Never assert a guessed legal effective day.

Public brief mirror: [SIH26265](https://zaidsayyed.in/tools/sih-problem-statements/sih26265)
is the baseline's discovery reference, not an official bank/AICTE authorization.
Production connectors and legal activation require explicit sponsor authorization.

## Baseline reconciliation

The baseline's extra artifact names are satisfied through canonical documents here:
architecture/backlog -> IMPLEMENTATION_PLAN and ARCHITECTURE_DECISIONS; source mapping
and domain rules -> policy package and REQUIREMENTS_MATRIX; threat model -> SECURITY_MODEL;
demo script -> DEMO_SCENARIOS. Avoid contradictory duplicate specifications.
New architecture decisions must retain required hard constraints and record rationale.


## Adopted independent review amendments

ADR-013: distinct security_deposit_obligations and typed deposit_records before migration; avoid FDR-only parent model. ADR-014: PENDING_SCRUTINY accepts safe substantive failures, acceptance remains blocked; incomplete mandatory evidence stays DRAFT. ADR-015: many valid role_bindings by institution/bureau/case, no global role; permanent subject separation. ADR-016: input_revision independent of command version; policy_revision + document_set_hash required for freshness. ADR-017: lifecycle skeleton moved to Phase 1B, then extend intelligence/hardening; no bypass for demonstration. ADR-018: API supports degraded intake with durable outbox during broker outage. ADR-019: canonical full financial references deferred to managed-key encryption; HMAC version explicit. ADR-020: release reasons TERM_COMPLETED/CLOSURE/MERGER/CONVERSION/OTHER have branch evidence/holds, not generic maturity eligibility.
