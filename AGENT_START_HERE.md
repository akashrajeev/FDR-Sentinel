# Agent Onboarding — SIH26265 FDR Sentinel

1. Read `ARCHITECTURE.md` thoroughly. It maps the current implementation; `docs/ARCHITECTURE_BLUEPRINT.md` preserves the original proposal. Consult `docs/STATUS.md` and `docs/VERIFICATION.md` for test evidence.
2. Respect the source-of-truth and policy boundaries: official AICTE APH 2024–27 clauses 1.12 and 6.46, and the SIH26265 problem statement. Before production usage check updates/corrigenda.
3. Treat all real bank/AICTE integrations as gated behind prior written authorization; build mock adapters first and label their output **SIMULATED**.
4. Do not write code that uses an LLM as the final adjudicator of regulatory eligibility or as the issuer of a release, NOC or RTGS sanction.
5. Implement modular monolith + worker architecture as specified. Prefer vertical functional slices and tests over creating empty microservice folders.
6. Begin with a detailed task backlog, clear dependencies, schema, endpoint contracts, and sample regulatory fixtures. Request architectural decisions before altering hard constraints.
7. Required acceptance: all D1–D10 scenarios in `docs/SIH_ACCEPTANCE.md`, plus deterministic rule and authorization tests, idempotency, and reproducible synthetic demo.
8. The supplied `docs/images/architecture-overview.jpg` is the current presentation view. The older SVG and blueprint are historical references, not a current dependency inventory.

## Suggested first agent command

> Study ARCHITECTURE.md and AGENT_START_HERE.md, propose a 4-stage implementation backlog with schema migrations and acceptance tests, identify any legal/regulatory ambiguities as assumptions, then implement Stage 0 and the Stage 1 non-AI core. No banking integrations or unsupervised decisions. Ensure docker compose boots with synthetic seeded demo records.
