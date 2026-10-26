# Implementation status

## Phase 7 — approved Registry UI and improved public home

Applied user-selected direction A from the design gallery to the real React portal:
white rail, navy typography, cobalt controls, flat tables, clearer evidence/form/report
layouts, keyboard navigation and responsive mobile behavior. The public home now has
an institutional product introduction, lifecycle/access guidance, one OIDC continuation
and explicit sandbox boundaries. No credentials or institutional records are fetched
on the public screen. There are no copied mockup portfolio numbers in the application.

Overview displays actual scoped summaries, intervention/clearance/overdue counts and
audit activity. The six-row recent preview links to a server-filtered 50-row paginated
register. Draft creation opens the persisted detail directly; record anchors expose
evidence, policy, sources, correction and history. Protected loading/error/empty states,
blocked decisions, source distinction and all existing business permissions remain.
Implementation scope and rationale: REGISTRY_UI.md.

Executed qualification:

- `npm run build --prefix apps/web`: TypeScript/Vite passed. `ruff check apps/api scripts
  tests`: passed. Existing dependency audit remains separate from production security.
- `docker compose --profile test run --rm --no-deps test`: **88 passed, 10 deselected
  in 112.44s**; `.local/registry-backend-qualified.log`.
- `.venv\Scripts\python scripts/fresh_acceptance.py --snapshot 20261022T000000Z`:
  **PASS**, isolated project `sentinel-acceptance-09c87226`, **88 passed, 10 deselected
  in 56.21s**, readiness passed, **191.25s total**. 143 source files, SHA-256
  `6cf1309f4cf69069da8d3d38fd547923b893e57fd76489723bbf2e4fd9e4edd3`.
  This export preceded final navigation and asynchronous-state refinements; those
  receive live browser verification. No cold-browser or hosted-CI claim. Fresh service
  logs/volumes are retained in `.local/fresh-acceptance-09c87226`; services stopped.
- Targeted home/auth/register checks: **2 passed in 21.88s**; final back-navigation
  recheck **1 passed in 8.88s**. Main workspace desktop/mobile overflow checks passed
  for Deposits, Institutions, Release cases, Reports and Audit trail. Public home and
  loaded overview were visually inspected. `.local/registry-qa` retains evidence.

Initial checks encountered stopped services and a host clock rollback that placed
retained operator grants in the future. Services were restored and time-based access
checks were preserved until those assignments became active; no grant was backdated,
no password reset and no authorization bypass were introduced. SMTP tests now search
their unique Mailpit subject rather than assuming a new email sorts into the latest
100 retained messages. Mobile table overflow caused by an off-screen label was fixed;
the first full browser run passed nine journeys and exposed obsolete emoji navigation
selectors in the tenth, which were updated.
Subsequent browser regression exposed stale reminder/report responses and an institution
selector that cleared an already-loaded policy when reselecting the same value. Added
request-revision guards, immediate reminder filtering, stale policy/notification guards
and preserved same-institution policy state. The two affected real-service journeys
passed together: **2 passed in 39.53s** (`.local/registry-browser-fixes.log`). Reminder
assertions now identify the exact instrument and as-of band, rather than any SENT email.

Final combined command `.venv\Scripts\python scripts/local.py -m pytest -q -m browser`:
**10 passed, 88 deselected in 189.42s** (`.local/registry-browser-complete.log`). Includes
actual OIDC, scoped registration/search, uploads/scanning/OCR, independent scrutiny,
source checks, bureau blocks/issuance, renewal, operator/CSV, SMTP intervention delivery,
acknowledgement/source resolution and the new public/mobile home. TypeScript/Vite and
Ruff passed after final application edits. `npm audit --prefix apps/web --audit-level=high`:
**0 vulnerabilities**; existing production OS/JDK/security qualification remains separate.

The approved local UI milestone is complete and deployed at localhost:8088. API readiness
is healthy with scanner/worker processing available. No financial state machine,
authorization rule, regulatory policy coverage or official-integration gate was changed.

## Phase 6 — detailed problem-statement gap closure (2026-10-27)

Implemented persistent interventions for missing/unsafe proof and release evidence,
pending/failed/conflicting source checks, scrutiny, unresolved discrepancies, bureau
clearance, active holds, maturity and unsupported regulatory context. Scheduled Celery
and manual scoped scans share one service. Product SLAs, maturity bands and independent
supervisor selection are versioned, reasoned and audited. Deadlines are not statutory.
Reminders/escalations create durable real SMTP work, deduplicated per episode/recipient;
delivery rechecks access/task state and cancels obsolete work. Acknowledgement cannot
resolve source facts or authorize anything. Resolved history remains immutable and
recurrence gets a new episode.

React Reports now has category/state/institution/deposit/overdue filters, complete scoped
counts, keyset pagination, source findings, acknowledgement, actual email status/retry,
policy configuration and audited safe CSV. Existing maturity UI filters its own notice
kind. Registry-only notices can have no deposit; their audit uses notification identity.
No genuine financial status, approval gate or regulatory scope was broadened.

An eight-case/five-iteration actual HTTP comparison measured 16 per-record proxy reads
versus one consolidated report read, both finding all eight fixed expected issues with
zero false positives/negatives. Medians: 0.2085s proxy, 0.0127s consolidated; monitor scan
0.0703s separately. This is a scripted synthetic proxy, not a measured human baseline or
real institutional savings. Ground truth and reproducible script are checked in;
MEASUREMENTS.md records boundaries. PROBLEM_STATEMENT_COVERAGE.md lists every remaining
external acceptance item: official authority/contracts, policy-owner applicability,
production security/operations, real human pilot and hosted CI.

Initial backend regression: **88 passed, 9 deselected in 99.09s**. New browser journey:
**1 passed, 96 deselected in 23.52s**. Final-source qualification:

- `docker compose --profile test run --rm test`: **88 passed, 9 deselected in 130.07s**;
  `.local/phase6-backend-qualified.log`. Actual PostgreSQL, IdP, scanner, objects, source
  HTTP and SMTP; includes registry-only email audit and queued-revocation cancellation.
- `.venv\Scripts\python scripts/fresh_acceptance.py --snapshot 20261022T000000Z`:
  **PASS**, 130 source files, fresh isolated project `sentinel-acceptance-8661d638`,
  **88 passed, 9 deselected in 67.53s**, readiness passed, **225.45s total**. Source hash
  `c2a16a826195a11d9e562efe274c5d15174707e4952177dd6b053a009a9e9836`.
  Manifest/logs/volumes retained under `.local/fresh-acceptance-8661d638`; its services
  stopped after verification and the main stack remained intact. Later documentation
  edits are outside this export hash. This was backend cold acceptance, not cold browser/hosted CI.
- Ruff, TypeScript/Vite build, regenerated OpenAPI/TypeScript and diff whitespace checks
  passed. `npm audit --prefix apps/web --audit-level=high`: **0 vulnerabilities**;
  this does not supersede the recorded OS/JDK advisory review.

- `.venv\Scripts\python scripts/local.py scripts/restore_drill.py`: **PASS**, public
  and sandbox schemas, **27 tables, 2,938 rows, 1,300 audit rows, 185 object hashes**,
  **14.59s**, source untouched. `.local/phase6-restore.json`; local recovery only.

- `.venv\Scripts\python scripts/local.py -m pytest -q -m browser`: **9 passed,
  88 deselected in 215.30s**; `.local/phase6-browser-qualified.log`. Includes actual
  policy/supervisor editing, worker SMTP escalation, acknowledgement, filtered CSV,
  source resolution and the previous eight complete journeys. Screenshots of escalation
  and resolution were visually reviewed; no layout failure was observed.

The local Phase 6 software milestone is complete. Git checkpoint follows this evidence
update. The remaining externally dependent acceptance requirements listed in
PROBLEM_STATEMENT_COVERAGE.md are **not complete**; no official authority, full legal
applicability, human-study improvement or production-security certification is claimed.
Intermediate fixture failures (incorrect RETURN enum/helper name and an assertion that
ignored pagination) were corrected. Additional review fixed the nullable registry
notification audit edge case and added its actual SMTP regression coverage.

## Phase 5C — completed SIH end-to-end milestone (2026-10-26)

The SIH milestone is complete with real local services and synthetic records. The React
portal covers onboarding, registry checks, scoped operator assignments, atomic CSV
intake, private document processing, evidence correction, deterministic policy checks,
officer scrutiny, maturity/email, independent renewal, bureau holds/clearances, human
approval/issuance, and separate bank/AICTE sandbox exchange and reconciliation.
See `SIH_ACCEPTANCE.md` for D1–D10 evidence and `SIH_DEMO_RUNBOOK.md` for judging steps.

Executed final verification:

- `.venv\Scripts\python scripts/local.py -m pytest -q -m browser`: **8 passed,
  80 deselected in 154.91s**. Real PKCE logins, HTTP APIs, PostgreSQL, S3, scanner/OCR,
  workers, source sandbox and SMTP were exercised. Evidence: `.local/milestone-browser-final.log`.
- `docker compose --profile test run --rm test`: **80 passed, 5 browser tests
  deselected in 44.29s** at Phase 5B. The expanded final-source backend suite was
  re-executed in the clean deployment below; browser additions account for the later
  eight deselections. Evidence: `.local/milestone-tests-b2.log`.
- `.venv\Scripts\python scripts/fresh_acceptance.py --snapshot 20261022T000000Z`:
  **PASS**, fresh generated credentials, images, database, private storage, source
  sandbox, IdP, worker and Mailpit in isolated project `sentinel-acceptance-1aaefc8e`.
  **80 backend tests passed, 8 deselected in 65.85s**; readiness passed; total **231.53s**.
  Source export: **121 files**, SHA-256
  `9afbacb3265c0b9e35f1ef06a99033e9e09efd6d5f8f68ab81044bf829fdca13`.
  Evidence retained under `.local/fresh-acceptance-1aaefc8e`; isolated services stopped
  after verification. This was a cold backend acceptance run; the browser run used the
  primary stack. Later documentation edits are not included in that source-export hash.
- `npm run build --prefix apps/web`, Ruff, generated OpenAPI/TypeScript contracts and
  `git diff --check`: passed. `npm audit --prefix apps/web --audit-level=high`: **0 vulnerabilities**.
- `.venv\Scripts\python scripts/local.py scripts/smoke_local_ai.py`: actual local
  Qwen2.5:0.5b connection, **2/3 fields retained with independent source linking**, one
  unsupported proposal rejected, **8.99s**. No original model quote passed validation.
- `.venv\Scripts\python scripts/local.py scripts/restore_drill.py`: **PASS**, both
  public/sandbox schemas, **25 tables, 1,679 rows, 719 audit rows, 160 object hashes**,
  **10.26s**, source untouched. Evidence: `.local/milestone-restore.json`.

Browser verification exposed and fixed stale renewal versions after maturity refresh,
ambiguous form labels, stale notices across navigation, and premature evaluation/submit
controls during evidence processing. Superseded evidence remains retained and excluded
from the active readiness gate. Removed the old echo-fixture buttons from the interactive
UI; historical fixture evidence remains explicitly labeled. Screenshots of import,
renewal and issued/reconciled output were visually inspected. Core runtime environment inspection found no owner,
IdP-admin, source fixture-admin, source DB password or demo-account secrets.

No known blocker remains for the documented local SIH flows. Phase 4B production
activation is **not complete**: written integration authority, current applicable
regulatory review, real institution onboarding, deployment/security qualification and
operational sign-off remain external work. No real money moves, bank confirmation,
official regulator receipt or legal-compliance certification is claimed. Optional AI
has a tiny synthetic evaluation, existing OS/JDK advisories remain documented, and
restore qualification is local only. No Git remote is configured, so hosted CI has not
run; its workflow exists and local verification is recorded here.

## Phase 5B — completed operator, legacy intake and SMTP workflows

Implemented authenticated technical-operator workspace and scoped grants/revocations,
with no operator self-grants, no financial authority from operator status, and bounded
validity. A narrowly scoped security-definer database command validates the operator,
target and scope and writes the assignment/audit atomically; direct runtime role-table
updates remain forbidden. New institutions can receive officers through the UI.

Added bounded UTF-8 CSV template/preview/commit; typed FDR/RTGS date validation, synthetic
reference/bank restriction, owner scope, duplicate checks, unchanged-preview hash and
idempotent transactional all-or-nothing intake. Imported records remain DRAFT.

Added real SMTP delivery into persistent Mailpit, stable Message-ID, deduplicated
notification work, attempts/backoff/dead letters and scoped human retry. SMTP acceptance
is not proof a person read mail; crash-after-send can cause at-least-once redelivery.
SMTP binds localhost:11025 and the test inbox localhost:8025. Initial port 51025 was
reserved by Windows; changed the local binding rather than altering system reservations.

Executed: `docker compose --profile test run --rm test`: **80 passed**, five browser
tests deselected, **44.29s**. New tests verify scope assignment/revocation and denials,
single audited idempotent grant, import preview/rollback/replay, actual message content
in Mailpit, worker replay without another send, actual refused SMTP connections through
dead letter and authorized recovery. Frontend TypeScript/Vite build and Ruff passed.

Fixed a failure exposed by integration immutability: implicit ORM autoflush could seal
SUCCEEDED before completion metadata was assigned. The processor now suppresses
intermediate autoflush and commits completed evidence in one update. Pending requests
were recovered through the normal processor (including a correctly STALE response),
without database edits. Phase 5C browser/fresh-stack acceptance follows.

## SIH completion extension — 2026-10-26

Phase 5A adds a real HTTP bank/AICTE sandbox backed by independently persisted fictional
ledger/registry records in an isolated PostgreSQL schema/role. The portal enqueues
durable authenticated verification requests, validates signed correlated responses,
handles pending/transient failures, retains stale results without endorsing new inputs,
and blocks known conflicting/incomplete checks. Human-issued outputs can be synchronized
to the case sandbox and reconciled with the bank sandbox. Sandbox completion remains
separate from real RELEASED/BANK_CONFIRMED, which remain prohibited. Catalogue and
exchange progress/source records are visible in the React portal.

Executed first run: `docker compose --profile test run --rm test`: **75 passed**, five
browser tests deselected, **43.98s**. Includes eight new actual-HTTP sandbox tests covering
matching/mismatched independent data, delays, HTTP 503 recovery, source signature and
correlation, stale input, source credentials, database-role isolation, and reconciliation
only after independent human issuance. A focused final-source recheck and frontend build
are recorded with the checkpoint. Production integration/regulatory activation remains
separate; Phase 5B operator/CSV/SMTP and Phase 5C full browser/fresh-stack acceptance follow.
Final-source focused recheck: `.venv\Scripts\python scripts/local.py --test -m pytest
-q tests/test_sandbox_integrations.py`: **8 passed in 40.13s**. Ruff and frontend
TypeScript/Vite build passed after the final source changes.

Earlier baseline: complete synthetic local workflows through Phase 3, with Phase 4A local
operational qualification below. Phase 4B production activation remains blocked. The
architecture/review are design inputs; this register is the actual evidence record.
Live local portal: http://localhost:8088. No real bank/AICTE or settlement connection.

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

## Phase 4A — completed local operational qualification

Implemented restricted PostgreSQL runtime grants, separate owner provisioning, guarded
onboarding scope inserts, explicit application-only runtime environment, read-only
container filesystem/temporary scratch/capability restrictions; payload-free OTel spans
with transactional outbox/Celery context and optional OTLP; safe generic HTTP errors;
configurable recent verified-MFA gate for approval/issuance with explicit demo exemption;
stable browser mutation retry keys; real lost-response browser regression; signed JWT
wrong-audience/expiry tests; strict input/privilege tests; actual outage, snapshot restore
and load scripts; operational/activation runbook and dependency review.

Keycloak 26.8.1 runs against a copied volume with the original/archive retained. The API
base is Debian Trixie/Tesseract 5.5.0. A recent signed snapshot build was needed because
upstream repository signatures were ahead of VM time. APT now fails on any repository
update error rather than accepting a partial update; signatures/expiry remain enabled.
Unused Pillow was removed; the final runtime excludes pip/ensurepip after installation.
Application-only Python/npm audits report no known findings, while unresolved scanned
OS/JDK advisories remain explicit production blockers in DEPENDENCY_REVIEW.md.

Executed evidence:

* `docker compose --profile test run --rm test`: **67 passed**, five browser tests
  deselected, **48.51s**, actual PostgreSQL/OIDC/private S3/scanner/Tesseract on the
  final image with the package installer removed. Earlier pre-removal run: 45.96s.
* `.venv\Scripts\python scripts/local.py -m pytest -q -m browser`: **5 passed**,
  67 deselected, **109.74s**, final runtime image and upgraded OIDC/Tesseract stack
  (earlier pre-installer-removal run: 143.63s). Includes actual PKCE,
  worker processing, officer review, pending-PGRC denial, independent synthetic issuance,
  scan annotations/corrections, simulated mismatch, scoped CSV and lost-commit-response
  retry for both JSON and multipart with identical returned IDs. Screenshots inspected.
* `npm run contracts --prefix apps/web` regenerates formatted types; TypeScript/Vite
  build and Ruff passed. Git diff confirms no schema/contract drift. Browser CI added;
  no hosted CI run has been executed.
* `scripts/load_check.py`: **200 requests**, concurrency 8, **0 HTTP errors**, p95
  **966.17ms** after seeding 1,000 synthetic institutions/deposits. Exact command,
  native-run/base-image timing and scope limitations are in MEASUREMENTS.md.
* Tesseract 5.5.0 recheck: **16/16** fields on four small synthetic fixtures; no claim
  of real-bank, handwriting or representative OCR accuracy.
* `.venv\Scripts\python scripts/local.py scripts/outage_drill.py`: actual Redis
  **11.16s** and ClamAV **109.09s** stop/recover checks passed. Both retained exactly
  one draft document, denied unsafe read and correlated the API upload trace with the
  real Celery worker. No approval occurred during outage or recovery.
* `.venv\Scripts\python scripts/local.py scripts/restore_drill.py`: isolated consistent
  restore verified **20 tables, 625 rows, 249 audit rows and 85 original/preview hashes**,
  **8.42s**. Restored database `sentinel_restore_d992791013` and private bucket
  `sentinel-restore-d992791013`; source retained. Ignored dump manifest includes SHA-256.
  This is local logical restoration, not production PITR/RPO/RTO or encrypted offsite proof.
* Runtime environment inspection confirmed no owner/admin/provisioning/demo passwords.
  Restricted-role SQL test rejects DDL, audit updates/deletes and officer scope grants.
  Query-text exclusion and outbox parent-context tests pass. Optional OTLP collector
  delivery and a real successful MFA ceremony are not claimed.

Fixed during qualification: long ID search accidentally also matched reference suffix;
now suffix matching only applies to four-character queries and wildcards are literal.
Native FastAPI tracing captured queries by default; disabled it in favor of explicit
safe spans. An MFA test initially used the wrong acknowledgement field; corrected.
One browser run overlapped deployment and got connection refusals; the readiness-complete
rerun passed. A native full backend attempt was stopped after inheriting enabled demo
AI; `--test` now disables it. Native OCR additionally needs Tesseract on PATH, so Docker
is the canonical full backend runner. Scanner cache-lock/download timeout attempts were
retried sequentially; failed attempts are not counted as vulnerability clearance.

Remaining production work (Phase 4B): current official amendment/effective-date/source
review, sponsor policy/signatory authority, authorized real connectors, production IdP
MFA/recovery and institutional proof, managed encryption/key rotation, retention/deletion,
independent immutable audit/PITR/recovery objectives, full deployment vulnerability triage
and independent security assessment. No actual release, settlement or legal certification
exists. Next milestone is sponsor-backed production qualification under the runbook gates.
