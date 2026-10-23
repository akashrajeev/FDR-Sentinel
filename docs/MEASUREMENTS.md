# Executed measurements

These are small synthetic test measurements, not estimates of regulatory impact or
bank verification accuracy. No manual-process baseline has been measured.

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
