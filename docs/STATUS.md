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

## Phase 2 — completed document intelligence and explicit simulations

Implemented real Tesseract OCR for raster PDFs; varied digital INR/date parsing;
page/bounds/hash evidence; protected worker-rendered page previews and browser region
annotations; proposed/independently confirmed extraction corrections; fresh-evaluation
and discrepancy-disposition acceptance gates; immutable original/decision guards;
optional local Ollama proposals with strict schema and independent source anchoring;
signed SIMULATED bank scenarios that cannot set BANK_CONFIRMED; NOT_CONNECTED AICTE
adapter; five-attempt dead letters with officer retry; database-specific Celery queues;
scanner/worker/broker degradation and structured request logs. Fixed Nginx DNS re-resolution.

Executed evidence:

* `docker compose --profile test run --rm test`: **45 passed** (13 unit + 32 integration),
  3 browser tests deselected, 28.68s. Actual PostgreSQL/Keycloak/S3/ClamAV/Tesseract.
* `.venv\Scripts\python scripts/local.py -m pytest -q -m browser`: **3 passed**,
  45 deselected, 50.89s. New path uploads a raster scan, invokes real worker OCR/local AI,
  draws a private evidence region, proposes and independently confirms transcription,
  reevaluates, and records a prominently SIMULATED mismatch without bank confirmation.
* Deterministic extraction: **16/16 exact fields on four small synthetic fixtures**,
  including one raster scan. Local AI smoke: **2/3 fields retained**, one unsupported
  proposal rejected, original quotes independently relinked. See MEASUREMENTS.md; no
  real-bank or handwriting accuracy is claimed.
* TypeScript/Vite and Ruff passed; browser screenshots inspected. Readiness returned
  ready/available for scanner, broker and recent worker heartbeat with no pending jobs.

Fixed during verification: bounded fixed-field model schema replaced an unstable array
response; unsupported/poor model output fails closed as advisory-only. UI actions now
share an in-flight guard to avoid stale-version races between evaluation and simulation.
An explicit accessible selector label fixed the browser scenario control. A development
VM/repository metadata clock skew required a bounded build-only APT future-time tolerance;
package signatures remained enabled. Dependency Starlette/httpx deprecation remains.

Remaining technical milestones: Phase 3 reporting/search/export and broader policy context
with explicit revalidation; Phase 4 fresh-stack waits, restricted database runtime role,
resilience/restore/load/security qualification and deployment runbooks. Official amendment
review, authorized signatories, production identity/MFA/data policies and genuine external
contracts remain sponsor dependencies. No real release/settlement is implemented or claimed.

## Phase 3 — completed reporting and policy/revalidation extension

Added paginated scoped search, complete-scope database aggregate dashboards, safe CSV
export with audit and spreadsheet-formula escaping; persisted synthetic case timing with
sample count and explicit automated-demo limitations; the broader cited Table 1.4 fixture
for programme/level combinations; single-record vs aggregate-review obligation scope;
fresh policy/evidence indicators; explicit revalidation that preserves prior decisions
and invalidates pending release clearances; release policy snapshots and conservative
bureau inventory; typed financial-embezzlement holds requiring EXTERNAL_BODY_NOC evidence;
configurable maturity bands; operator scope provisioning with reasons/validity and audit.
Aggregate monetary totals use exact decimal strings, avoiding JavaScript integer overflow.

Executed evidence: `docker compose --profile test run --rm test`: **60 passed**, four
browser tests deselected, 17.61s. `.venv\Scripts\python scripts/local.py -m pytest -q -m
browser`: **4 passed**, 60 deselected, 50.50s. TypeScript/Vite and Ruff passed. Reporting
screen inspected, actual authenticated CSV download verified. All prior workflow gates
remain tested. Policy v1 remains in the repository; evaluation snapshots retain old sources.

Limits: programme tables do not settle historical eras, existing-deposit credits,
multi-programme aggregates, authentic bank data or current amendments. Such contexts
remain human-review paths, and all legal activation is blocked. No production regulatory
coverage is claimed. Phase 4 operational qualification is next.
