# FDR Sentinel engineering contract

Read AGENT_START_HERE.md, ARCHITECTURE.md and docs/IMPLEMENTATION_PLAN.md.
Architecture is a proposal; docs/STATUS.md records actual implemented/tested status.
Keep a modular monolith, PostgreSQL, OIDC, explicit transitions, scoped authorization,
transactional audit/outbox and idempotency. Never invent financial/regulatory approval.
Use synthetic records only. No real bank/AICTE connector without written authorization.
Workers and AI cannot make officer decisions or authorize release. No release endpoint
until independent bureau clearances, holds and issuer authorization are implemented.
Policy fixtures are provisional until current official amendments and applicability
are reviewed. Unknowns require human review. Do not silently broaden policy coverage.
Run relevant PostgreSQL integration tests and frontend typecheck/build before checkpoints.
Record exact commands/results and limitations. Never commit .env, credentials or uploads.
