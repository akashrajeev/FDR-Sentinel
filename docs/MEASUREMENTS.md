# Executed measurements

These are small synthetic test measurements, not estimates of regulatory impact or
bank verification accuracy. No manual-process baseline has been measured.

## Final SIH acceptance (2026-10-26)

The final combined browser run passed **8 tests in 154.91s**. A separate clean source
deployment with fresh credentials and isolated persistent volumes passed **80 backend
tests in 65.85s**, readiness, and startup in **231.53s total**. This measures this local
Docker environment and synthetic fixtures, not production throughput or human review
time. Exact commands, source-export hash and limitations are in `STATUS.md`.

The latest real Ollama smoke retained **2/3 correct fields**, rejected one unsupported
proposal and took **8.99s**. Zero original model quotes validated; both retained fields
were independently linked to source text. This repeats the limited result below rather
than demonstrating improved extraction accuracy.

The latest local snapshot restore verified both public/sandbox schemas: **25 tables,
1,679 rows, 719 audit rows and 160 object hashes in 10.26s**, source untouched. This is
a synthetic local recovery drill, not a production RPO/RTO/PITR commitment.

## Document extraction (2026-10-23)

Command: `docker compose run --rm -T --no-deps api python scripts/benchmark_extraction.py`.
Algorithm `typed-digital-tesseract-v2`; PyMuPDF 1.28.2; Tesseract 5.3.0; English OCR;
180 DPI raster processing on local Docker Desktop. AI assistance disabled for this test.
Ground truth is separate from the fixture generator: `tests/fixtures/extraction_ground_truth.json`.

| Sample | Fields correct / expected | False positives | Processing seconds | OCR pages |
|---|---|---|---|---|
| digital-a | 4 / 4 | 0 | 0.046 | 0 |
| digital-b | 4 / 4 | 0 | 0.022 | 0 |
| scanned | 4 / 4 | 0 | 0.974 | 1 |
| adversarial instructions | 4 / 4 | 0 | 0.018 | 0 |

Observed exact-field precision 16/16 and recall 16/16 on **four** synthetic printed
layouts (one raster scan). This is not a representative corpus, handwriting evaluation,
authenticity check or legal-compliance result. Production evaluation needs independently
labeled authorized documents, more layouts/languages/scans, held-out data and error analysis.

## Local AI smoke

Command: `.venv\Scripts\python scripts/local.py scripts/smoke_local_ai.py`.
Actual installed Ollama server 0.12.6; Qwen2.5:0.5b model observed digest
`a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67`.
One synthetic sample, three expected fields: **two retained correct fields, one unsupported
proposal rejected**, 5.31 seconds in the recorded run. Zero original model quotes passed
the full field/value quote check; both retained fields were independently relinked to
exact page evidence by the deterministic parser. Repeated local runs varied.

This demonstrates a connected assistive model and strict evidence validation. It does
not show that this small model improves extraction accuracy. AI proposals never replace
original evidence, create authenticity, decide compliance or authorize a release. Only
an independent human-confirmed correction can enter the deterministic evaluation.

## Workflow time and operational metrics

Automated browser suite times are recorded in STATUS.md. They include scripted logins,
service waits and automated actor switching, and are not human review turnaround times.
No percentage savings or ROI is claimed. The reporting milestone derives synthetic case
durations from persisted create/issuance audit timestamps with a sample count and scope.
Prometheus request metrics use route templates, not institution IDs or financial references.

## Local read-load qualification

Command: `.venv\Scripts\python scripts/local.py --test scripts/load_check.py`.
Actual loopback HTTP, PostgreSQL and OIDC; temporary single Uvicorn process running as
`sentinel_runtime`; 1,000 newly seeded synthetic institutions/deposits plus existing
test rows; 200 alternating scoped-summary/search requests, concurrency 8.
Observed **0 HTTP failures**, 17.28 seconds, **11.57 requests/second**, median 683.62 ms,
p95 **966.17 ms**. This run preceded the final Trixie image update and ran the same
application read paths natively. It is not production capacity or upload/OCR throughput.
No production SLO is inferred from it. Fixtures are preserved in sentinel_test.

## Tesseract base-image recheck

Command: `docker compose exec -T api python scripts/benchmark_extraction.py` after the
Debian Trixie/Tesseract 5.5.0 update. Again **16/16 exact fields**, zero false positives/
negatives across the same four tiny synthetic fixtures. Digital-a 0.044s, digital-b
0.026s, raster 0.916s, adversarial-text layout 0.017s. All earlier corpus limitations
still apply; this recheck verifies no observed regression from the engine update.

## Outage and recovery evidence

`scripts/local.py scripts/outage_drill.py` stopped actual local Redis and ClamAV, then
recovered them in finally paths. Observed cycles: Redis 11.16s, ClamAV 109.09s. Both
accepted durable synthetic intake, denied unsafe reads, recovered exactly one READY
document and retained DRAFT workflow. API upload trace IDs appeared in actual worker
document.process spans through the broker/outbox, including recovery. Timing depends
on local service startup, retry schedule and optional model; it is not a recovery SLA.

`scripts/local.py scripts/restore_drill.py` used one exported consistent snapshot and
isolated DB/bucket. **20 tables / 625 rows / 249 audit rows / 85 object hashes**, 8.42s,
source retained. Dump SHA-256:
`26d327a83a5292ea7d498d5a3ec29087b42f4a4b5bf6e44f924e1b528f3a0f75`.
The first prior run with IPv6-fallback localhost endpoints took 279.78s for fewer rows;
the final run used explicit 127.0.0.1 through local.py. These are local logical restore
observations, not production backup encryption, offsite immutability, RPO or RTO claims.
