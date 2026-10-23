# FDR Sentinel

SIH26265 · institutional security deposits and FDR workflow platform.
See [implementation plan](docs/IMPLEMENTATION_PLAN.md), [decisions](docs/ARCHITECTURE_DECISIONS.md)
and [actual status](docs/STATUS.md). Architecture documents describe intended capabilities;
the status register records executed evidence. This is a synthetic local system, not an
authorized AICTE/bank integration or regulatory certification.

## Local deployment

Requires Docker Compose, Python 3.12+ and Node 24 (Node needed for development/type generation).

```powershell
python scripts/bootstrap.py
docker compose up --build -d
docker compose ps
```

Open http://localhost:8088. Identity provider: http://localhost:8081. Initial antivirus
definitions and image pulls can take several minutes. Files stay quarantined until the
real scanner succeeds. Credentials are randomly generated in ignored `.env` (never commit
or share it). Users: `institution`, `other-institution`, `reviewer`, `pgrc`, `vigilance`,
`approver`, `issuer`, `auditor`. Match user to `DEMO_<USER>_PASSWORD` in `.env`.
`institution` owns the synthetic seeded institution; other accounts have explicit scopes.
Onboarding a new institution does not automatically assign reviewers; use the operator
provisioning command described below when developing new scoped scenarios.

All dependency ports bind loopback; do not expose this development stack publicly.
PostgreSQL :55432, Redis :56379, private S3 :59000, ClamAV :53310. Object storage uses
SeaweedFS behind the standard S3 interface (ADR-021). API internal OpenAPI `/openapi.json`.
The browser only calls real API endpoints, and uses Keycloak authorization code + PKCE.

## Development and verification

```powershell
uv venv
uv pip install -r requirements.lock
uv pip install --no-deps -e .
npm ci --prefix apps/web
.venv\Scripts\python scripts/export_openapi.py
npm run contracts --prefix apps/web
npm run build --prefix apps/web
.venv\Scripts\ruff check apps/api scripts tests
.venv\Scripts\python scripts/local.py --test -m pytest -q -m "not browser"
```

Integration tests create/migrate only the dedicated `sentinel_test` database and preserve
unique synthetic rows. They authenticate against actual Keycloak and use actual S3 and
ClamAV. Unit tests can run without the stack: `pytest tests/test_rules.py`.
`scripts/local.py` loads ignored credentials without echoing them. Windows background
Celery uses `--pool=solo`; the Docker worker is the normal development path.

```powershell
docker compose --profile test run --rm test
```

Compose test is the equivalent Linux runner. The portal never uses password grant;
the development realm's test-only client does so for reproducible API tests. Production
startup is deliberately gated. See SECURITY_MODEL.md for qualification work.

## Boundaries

Money is INR integer paise. Original financial references are not retained: keyed digest
+ last four, with HMAC version. Canonical reference reconciliation needs future managed-key
encryption. Evidence uploads are immutable originals; new evidence can explicitly supersede
old evidence while preserving it. Rules are narrowly scoped, versioned, provisional APH
2024-27 fixtures. Unknown legal context requires review. Manual review never claims bank
authenticity. AI/workers cannot authorize regulatory or financial decisions.

The Release cases tab now demonstrates scoped PGRC/Vigilance/Grants clearances,
independent approval and type-specific synthetic issuance. Only synthetic NOC/sanction
outputs are generated; they carry no financial authority and do not mark settlement.
The same tab provides maturity monitoring and authorized replacement/renewal lineage.

## Documents and optional local AI

The worker scans with ClamAV, extracts digital PDF fields and runs real Tesseract OCR
for scanned pages. The portal provides protected page previews, bounded evidence
annotations, independently confirmed transcription corrections and discrepancy disposition.
Generate realistic samples with `python scripts/generate_fixtures.py` in the installed
environment; all resulting PDFs are visibly synthetic and stored under ignored `.local/`.
See [executed measurements](docs/MEASUREMENTS.md) for the tiny corpus and limitations.

Optional local Ollama: set `AI_ASSIST_ENABLED=true` and `AI_BASE_URL` in ignored `.env`,
pull `qwen2.5:0.5b`, then recreate API/worker. Docker Desktop can reach an installed host
server at `http://host.docker.internal:11434` (verified here). Alternatively use the
Compose `ai` profile and `AI_BASE_URL=http://ollama:11434`; the model service is optional
because its image is large. No external AI vendor is configured. Proposals are strictly
advisory; source text and human confirmation govern their use.

The local bank adapter is prominently SIMULATED. Its MATCH scenario echoes declarations
and its HMAC is a local demo signature, not bank PKI. It never sets BANK_CONFIRMED.
The AICTE adapter reports NOT_CONNECTED. Genuine integrations remain authorization-gated.

If a development Docker VM clock lags signed Debian repository metadata, this session
needed `docker compose build --build-arg APT_MAX_FUTURE_SECONDS=7200 api`. Default builds
retain strict 10-second tolerance. Package signatures/expiry checks stay enabled; fix
host/VM time synchronization before any production qualification.

Never run destructive volume resets on any environment with needed data. For local
restarts use `docker compose stop` / `docker compose up -d`; named volumes retain records.
