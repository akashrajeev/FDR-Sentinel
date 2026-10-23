# Architecture decisions

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
