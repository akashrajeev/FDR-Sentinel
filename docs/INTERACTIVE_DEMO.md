# Browser demo and Vercel deployment

Public URL: https://fdr-sentinel-demo.vercel.app . Choose **Explore interactive demo**;
no application credentials or Vercel account are required on this canonical URL.
Generated preview/deployment URLs may still require Vercel authentication.

The public judging demo shares the real React interface. Its data and transitions
run entirely in the browser; the FastAPI/PostgreSQL/OIDC application is unchanged.
The public entry offers **Explore interactive demo**, with no credentials. A normal
local build also keeps **Sign in securely**. Demo personas never issue an API token.

## Run and publish

```powershell
npm run typecheck --prefix apps/web
npm run build --prefix apps/web
npm run build:demo --prefix apps/web
npm run preview:demo --prefix apps/web
```

Open http://127.0.0.1:4174 and choose Explore interactive demo. The simulation is
selected by `?demo=1`; `vite --mode demo` removes backend sign-in from the public
entry. `npm run build` keeps the local OIDC path. Both use the existing UI.

Run `python scripts/package_demo.py` after qualification. It packages only compiled
HTML/JS/CSS/SVG and the explicitly allowlisted logo PNG, plus static hosting
configuration under ignored `.local/vercel-demo/`.
Its local manifest records asset digests and must not itself be uploaded. Upload
only its listed files using Vercel's connected deployment tools. No repository-wide
upload, backend, `.env`, credential, database dump, source upload or user document is
required. This is a static deployment with no paid backend resources or integrations.

## Feature coverage

| Local application capability | Judging demo representation |
|---|---|
| OIDC and scoped roles | Credential-free named personas, separate browser bindings; never security evidence |
| Overview, work queue, register and filters | Derived from the visitor's own synthetic records, with pagination |
| Institution onboarding and obligations | Local declaration, separate obligation, conservative sample applicability |
| FDR/RPGF/RTGS/ONLINE/legacy records | Seeded examples and forms; positive integer paise and instrument-specific dates |
| PDF upload, quarantine, validation and supersession | Local PDF header/size/SHA-256 checks, original sample snapshots, superseded history |
| Antivirus, digital extraction, OCR and worker recovery | Explicit sample outcomes, quarantine/pending/rejected/failed examples, bounded simulated retry |
| Advisory AI and evidence annotations | Precomputed proposals, draggable sample region, independent proposal/confirmation/rejection |
| Evaluation, discrepancies and scrutiny | Freshness checks, return/correction, source-linked resolution, human acceptance |
| Provisional policy and revalidation | Exceptional/unknown context stays human review; stale sample and retained decisions |
| Bank and registry verification | Labelled sample results, mismatch/not-found, pending/retry/dead-letter paths; no BANK_CONFIRMED |
| Renewal and replacement | Requested lineage, separate reviewer, later covering instrument, original retained |
| Maturity and configurable reminders | Demonstration clock, configurable day bands, deduplicated in-app examples |
| Operational interventions and escalations | Source-governed tasks, filters, acknowledgement, product SLA/supervisor configuration |
| Email delivery/recovery | Local simulated inbox, delivery states and retry; no real messages |
| Release cases and evidence | Draft/submit/return, supporting categories and synthetic upload samples |
| Bureau clearance, holds, approval and issuance | Independent personas, pending/rejected decisions, holds, separate approval and issuer |
| NOC vs RTGS sanction | Different labelled synthetic PDF outputs, never official authority or payment |
| Issuer sandbox receipt/reconciliation | Simulated exchange history; no actual external systems or settlement |
| CSV import and exports | Local synthetic CSV validation, preview hash, atomic batch rollback, draft import, full filtered export |
| Operator assignments | Fictional scoped grants, disable/enable, no self/operator grants; browser only |
| Audit and evidence | Resettable browser history with decision evidence; never claimed immutable |
| Theme and mobile interface | Existing Device/Light/Dark controls and responsive screens |

All frontend actions have either a local implementation or a clearly labelled
synthetic equivalent. Backend-only infrastructure (PostgreSQL transactions, durable
outbox, malware engines, source authentication, MFA, telemetry, backups and restore)
is described as backend evidence, not fabricated as running in a static browser.
The browser fixture intentionally covers less regulatory applicability than the
backend; unsupported contexts require human review rather than an invented result.

## Isolation and limits

Progress uses versioned localStorage. Reset restores all scenarios for that browser;
other visitors have independent copies. Storage failure falls back to memory. Tabs
are not synchronized. Editing browser data or changing personas is possible by
design and is never evidence of backend authorization or audit integrity.

Files are read on the user's device only. Unrecognized PDFs remain quarantined
without extraction and are not retained. Recognized synthetic samples get explicitly
simulated processing; no antivirus/OCR/model request is made. Browser CSV validation
is synthetic-only and rejects non-SYN bank/reference values. Existing backend upload,
OCR, OIDC and independent network sandbox paths remain available through local sign-in.

## Qualification commands

```powershell
$env:DEMO_BASE_URL = 'http://127.0.0.1:4174'
.venv/Scripts/python -m pytest tests/test_demo_browser.py -q
docker compose --profile test run --rm --no-deps test
.venv/Scripts/python scripts/local.py -m pytest -q -m browser tests/test_browser.py
```

The demo suite uses actual Chrome and static files. It rejects backend/OIDC network
requests and checks blocked decisions, independent issuance, PDF contents, corrections,
storage/visitor isolation, mobile layout, local file intake, recovery and CSV rollback.
Screenshots and synthetic exports stay ignored in `.local/demo-qa/`.
See STATUS.md for executed results, deployment identity and remaining limitations.
