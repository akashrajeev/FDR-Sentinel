# Verification and CI notes

## Current hosted failure

Inspected 28 October 2026. Current main and the only listed run point to
`0894f53e7a01997b153bd765c9df9c9dc18f27a3`.

- [Failed run](https://github.com/akashrajeev/FDR-Sentinel/actions/runs/40215413526)
- [Integration job](https://github.com/akashrajeev/FDR-Sentinel/actions/runs/40215413526/job/121235376180)

The backend Compose test step and frontend build completed. Ruff then exited 2:

```text
Failed to initialize cache at /app/.ruff_cache: Read-only file system (os error 30)
Cause: Failed to create temporary file
```

This is a lint-tool startup failure, not a failing test assertion or a clean lint result.
The API inherits `read_only: true` from Compose's `x-app`. `/tmp` is writable tmpfs, but
Ruff defaults to a project cache under `/app`. Later host/browser/audit steps were skipped.

A separate error occurred while uploading failure diagnostics: the account's artifact
storage quota was exhausted. Fixing that upload alone would not fix Ruff.

## Review-branch changes

- Run standalone container lint as
  `docker compose run --rm --no-deps api ruff check --no-cache apps/api scripts tests`.
  Lint reads source only, so it needs neither dependency startup nor cache writes.
- Retain read-only hardening. Do not set `continue-on-error` on tests or lint.
- Make only the failure-diagnostics upload best-effort with one-day retention. Quota
  exhaustion may still prevent that optional upload; no existing artifact is deleted.

No paid storage change, Actions rerun, push or merge is included in this local review.
The workflow remains push/PR-triggered with its existing 25-minute job timeout. Publishing
it can consume Actions minutes and requires approval for the intended run count/cap.

## Local review checks

Source: unmodified archive supplied as pinned `0894f53`; README, Compose, pyproject,
Dockerfile and CI content were reconciled with native live GitHub reads. Original Git
objects were not supplied. The review branch uses an explicitly labeled snapshot base,
not fabricated upstream commit ancestry. Apply the provided patch to a true clone for PR.

Executed locally on the review snapshot, 28 October 2026:

- Ruff 0.17.2, `python -m ruff check --no-cache apps/api scripts tests`: passed.
- Permission-denied cache reproduction on a non-writable snapshot root: default lint
  exited 2 during cache initialization; identical source with `--no-cache` exited 0.
  This supports the diagnosis but is not a container-filesystem requalification.
- `npm ci --prefix apps/web`: completed; reported zero vulnerabilities.
- `npm run typecheck --prefix apps/web`: passed.
- `npm run build --prefix apps/web`: passed, 53 modules (Node 22.23.4, not CI's Node 24).
- `npm run build:demo --prefix apps/web`: passed, 53 modules.
- `npm audit --prefix apps/web --audit-level=high`: passed, zero vulnerabilities.
- Workflow YAML invariants: lint/tests mandatory, only artifact upload best-effort; passed.
- Changed-document local links, source anchors and `git diff --check`: passed.
- README, architecture, judge guide and verification rendered and visually inspected.

These checks do not prove a hosted green run. The review environment has no Docker and
uses Python 3.10, not the project's Python 3.12 runtime. Full backend integration,
container execution, real-service browser paths and CI's Node 24 remain unrerun here.
No parallel demonstration services or data were changed by this review.

## Preserve the evidence boundary

`STATUS.md` and `MEASUREMENTS.md` contain earlier local qualification with exact commands.
They are historical source records, not fresh results from this review. Browser simulation
checks, real-service backend checks and live browser checks are separate evidence classes.
A passed automated journey is not a human task-time measurement.

Do not reset volumes or disable scanning/signature checks to obtain a pass. Production
qualification and authorized external acceptance remain open.
