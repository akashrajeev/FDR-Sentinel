"""Measure exact typed-field extraction against separately maintained fixture labels."""
import json
import time
from pathlib import Path

from sentinel.extraction import ALGORITHM, extract_document
from sentinel.synthetic import fixture_pdf


def benchmark():
    truth = json.loads((Path(__file__).resolve().parents[1] / 'tests/fixtures/extraction_ground_truth.json')
                       .read_text(encoding='utf-8'))
    rows = []
    totals = {'true_positive': 0, 'false_positive': 0, 'false_negative': 0}
    for name, expected in truth['cases'].items():
        started = time.perf_counter()
        evidence, metadata = extract_document(fixture_pdf(name), use_ai=False)
        observed = {(e['field'], str(e['value'])) for e in evidence}
        labels = {(key, str(value)) for key, value in expected.items()}
        tp, fp, fn = len(observed & labels), len(observed - labels), len(labels - observed)
        totals['true_positive'] += tp
        totals['false_positive'] += fp
        totals['false_negative'] += fn
        rows.append({'case': name, 'true_positive': tp, 'false_positive': fp, 'false_negative': fn,
                     'elapsed_seconds': round(time.perf_counter() - started, 3), 'ocr_pages': metadata['ocr_pages']})
    tp, fp, fn = totals.values()
    return {'algorithm': ALGORITHM, 'label_version': truth['label_version'], 'documents': len(rows),
            'expected_fields': tp + fn, **totals, 'precision': tp / (tp + fp) if tp + fp else 0,
            'recall': tp / (tp + fn) if tp + fn else 0, 'cases': rows, 'limitations': truth['limitations']}


if __name__ == '__main__':
    print(json.dumps(benchmark(), indent=2))
