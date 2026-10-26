# SIH completion milestone — 2026-10-26

Goal: real application services and network exchanges using explicitly synthetic data.
No genuine bank/AICTE connection, legal certification or money movement is introduced.

1. **5A Independent sandboxes and integrations:** one external-system sandbox API,
   isolated PostgreSQL schema/role, independent bank ledger and institution registry,
   authenticated HTTP requests, signed correlated responses, persistent pending/retry/
   dead-letter states, stale-input protection and human-triggered release reconciliation.
   Acceptance: actual HTTP/PG integration tests, adverse responses, replay/signature/scope
   denials, visible UI states and a frontend build before checkpoint.
2. **5B Operator and delivery workflows:** tightly scoped operator provisioning API/UI,
   transactional validated CSV intake, real SMTP to a persistent local Mailpit inbox,
   visible delivery attempts/retries. Acceptance: privilege and all-or-nothing import
   tests; actual SMTP delivery and failure recovery; frontend build before checkpoint.
3. **5C Complete acceptance:** D1-D10 browser/API coverage, isolated fresh-environment
   startup, reproducible seeded scenarios, regression/build checks and updated runbook,
   evidence register and Git checkpoint. Existing volumes are never reset.

The platform stays a modular monolith. A sandbox is a stand-in for an external
institution, not a split of core business services. Its registry/ledger cannot be
populated by echoing a verification request. Published fixture examples are fictional.
Its protocol is an assumed local contract, not an assertion of official API compatibility.

Keep genuine-verification and RELEASED database prohibitions. Sandbox results and
completion remain separate from human approvals and real financial states. A worker
may process a signed acknowledgement only after an independently human-issued output.
Production activation, current regulatory source review and unresolved OS/JDK findings
remain separately recorded in STATUS.md and DEPENDENCY_REVIEW.md.
