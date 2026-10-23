# Implementation status

## Phase 0

Completed architecture review and eight requested design documents. Reviewed both source
Markdown files and SVG; PNG absent. Official APH source checked, source/amendment
uncertainty explicitly documented. Every requested capability maps to phase and evidence.
No application functionality claimed at this checkpoint.

## Phase 1A — completed registration/scrutiny slice

Implemented: FastAPI + React/TypeScript, Alembic/PostgreSQL, Keycloak PKCE and JWT
verification, many scoped role bindings, declared onboarding, distinct obligations,
FDR/RPGF/RTGS/ONLINE/legacy records, exact paise, masked/HMAC references, private S3
originals, fail-closed ClamAV, Celery/Redis outbox processing, digital PDF page/bounds
extraction, cited deterministic provisional evaluations, deficient scrutiny, correction,
evidence supersession, officer return/acceptance, durable idempotency, optimistic locks,
append-only audit trigger, readiness/metrics/request IDs and Compose/CI configuration.

Executed evidence (2026-10-23):

| Command | Actual result |
|---|---|
| `.venv\Scripts\python scripts/local.py --test -m pytest -q -m "not browser"` | 24 passed in 56.56s |
| `docker compose --profile test run --rm test` | 24 passed in 4.56s on Linux, real PostgreSQL/Keycloak/S3/ClamAV |
| `.venv\Scripts\python scripts/local.py -m pytest -q -m browser` | 1 passed in 13.31s; real PKCE browser -> upload -> Celery -> officer acceptance |
| `npm run build --prefix apps/web` | TypeScript and Vite production build passed |
| `.venv\Scripts\ruff check apps/api scripts tests` | Passed |
| `docker compose build api web` and `docker compose up -d --no-build ...` | API healthy; web/worker/Beat and all backing services running |

Browser screenshots inspected in `.local/browser/`; no page JavaScript errors. Local
service writes/persistence and actual antivirus EICAR detection are tested. Initial
failures fixed: unavailable MinIO images (ADR-021), TS contract unions, concurrent Docker
build export collision, Linux pytest import path, absent Playwright headless executable
(used installed Chrome). Dependency deprecation warning remains for Starlette/httpx;
the deliberate forged-HMAC test also warned about its short invalid key.

Incomplete: lifecycle/release (Phase 1B), OCR/AI and simulated bank attestation (Phase 2),
full historic policy/exceptions, production MFA/key management/retention, trace export,
load and restore qualification. No bank/AICTE integration, legal certification, release
or payment is claimed. Next milestone: live PGRC-blocked synthetic lifecycle path.

## Phase 1B — completed thin lifecycle skeleton

Added calendar-based maturity state/in-app reminders; deduplicated notifications;
requested and independently authorized replacement/renewal lineage; typed release cases;
separate scanned release evidence; PGRC/Vigilance/Grants decisions; exception evidence
and holds; return/correction with retained invalidated clearances; independent approval;
type-specific independently issued SYNTHETIC NOC/sanction PDFs in private storage.
Case-only scopes do not grant institution-wide access. Permanent subject comparisons
prevent maker/checker bypass after role changes. Originals and clearance history have
database guards. No release settlement or payment movement exists.

Executed evidence:

* `docker compose --profile test run --rm test`: **36 passed**, 2 browser tests deselected,
  12.98s. Includes pending PGRC, cross-bureau denial, RTGS no invented FDR dates/sanction,
  closure/merger/conversion/other holds, stale concurrent officers, scope/role-change
  restrictions, deduplicated reminders and retained replacement lineage.
* `.venv\Scripts\python scripts/local.py -m pytest -q -m browser`: **2 passed**,
  36 deselected, 25.01s. Real sessions for maker, reviewer/Grants, Vigilance, PGRC,
  approver and issuer; approval actually rejected while PGRC pending, then synthetic
  issuance completes. Both result screenshots visually inspected.
* TypeScript/Vite build and Ruff passed; updated Compose API/web/worker/Beat running.

Fixed failure: locked SQLAlchemy reads must refresh existing identity-map objects;
otherwise a competing clearance could observe stale in-memory version after waiting.
Regression now races two distinct bureau actors and requires one 200 / one 409.
Browser selector was adjusted to include the navigation icon's accessible name.

Remaining: Phase 2 OCR/optional AI assistance, realistic extraction measurements,
SIMULATED bank-source adapter and degradation/dead-letter controls; extended historic
policy cases, reporting/exports; Phase 4 security/load/restore qualification. The eight
design documents and provisional-source restrictions remain applicable. This checkpoint
is a working synthetic lifecycle, not a production certification or authorized integration.
