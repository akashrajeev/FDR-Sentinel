"""Actual HTTP comparison of scripted per-record inspection and consolidated follow-up.

Creates a new fictional institution through authorized APIs; never edits SQL or resets data.
This is a reproducible proxy exercise, never a measured human/manual-process baseline.
"""
import json
import os
import statistics
import time
from pathlib import Path
from uuid import uuid4

import httpx
from sentinel.synthetic import fixture_pdf

CONTEXT = {'academic_year': '2026-27', 'governance': 'PRIVATE', 'programme': 'ENGINEERING_UG',
           'land': 'OWNED', 'exceptional_context': False}


def benchmark():
    truth = json.loads((Path(__file__).resolve().parents[1] / 'tests/fixtures/operations_ground_truth.json').read_text())
    api_url = os.environ.get('BENCHMARK_URL', 'http://localhost:8088')
    if api_url != 'http://localhost:8088':
        raise RuntimeError('Exercise is restricted to the local synthetic portal')
    clients = {}
    for name in ('institution', 'reviewer', 'operator'):
        token = httpx.post(os.environ['TEST_OIDC_URL'], data={'client_id': 'sentinel-tests',
            'grant_type': 'password', 'username': name, 'password': os.environ[f'DEMO_{name.upper()}_PASSWORD']}, timeout=15)
        token.raise_for_status()
        clients[name] = httpx.Client(base_url=api_url + '/api/v1/', timeout=30,
            headers={'Authorization': 'Bearer ' + token.json()['access_token']})
    maker, reviewer, operator = (clients[n] for n in ('institution', 'reviewer', 'operator'))
    def command(client, path, body=None, **kwargs):
        response = client.post(path, json=body, headers={'Idempotency-Key': str(uuid4())}, **kwargs)
        response.raise_for_status()
        return response.json()
    def get(client, path, **kwargs):
        response = client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()
    institution = command(maker, 'institutions', {'external_id': 'SYNTHETIC-BENCH-' + uuid4().hex[:20],
        'legal_name': 'Fictional controlled comparison ' + uuid4().hex[:8], 'context': CONTEXT})
    command(operator, 'operator/assignments', {'subject': get(reviewer, 'me')['subject'], 'role': 'REVIEWER',
        'scope_type': 'INSTITUTION', 'scope_id': institution['id'], 'reason': 'Assign fictional comparison exercise scrutiny.'})
    obligation = command(maker, 'obligations', {'institution_id': institution['id'], 'regulatory_event': 'NEW_INSTITUTION'})
    labels, identities = set(), []
    for sample in truth['cases']:
        deposit = command(maker, 'deposits', {'obligation_id': obligation['id'], 'deposit_type': 'FDR',
            'bank_code': 'SYN-BENCH', 'reference': 'SYN-' + uuid4().hex, 'amount_paise': 350000000,
            'issue_date': '2026-01-01', 'maturity_date': '2030-01-01'})
        identities.append((sample['name'], deposit['id']))
        labels.update((deposit['id'], category) for category in sample['expected'])
        if sample['proof']:
            response = maker.post(f"deposits/{deposit['id']}/documents", data={'category': 'DEPOSIT_PROOF'},
                files={'file': ('synthetic.pdf', fixture_pdf('digital-a'), 'application/pdf')},
                headers={'Idempotency-Key': str(uuid4())})
            response.raise_for_status()
            deadline = time.monotonic() + 90
            while True:
                detail = get(maker, f"deposits/{deposit['id']}")
                if all(d['status'] == 'READY' for d in detail['documents']):
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError('Real scanner/worker did not finish')
                time.sleep(0.5)
        if sample['bank']:
            ledger = 'SB-' + uuid4().hex
            if sample['bank'] != 'NOT_FOUND':
                response = httpx.post(os.environ['SANDBOX_URL'] + '/v1/fixtures/ledger',
                    headers={'Authorization': 'Bearer ' + os.environ['SANDBOX_ADMIN_KEY']}, timeout=10,
                    json={'id': ledger, 'institution_external_id': institution['external_id'],
                        **{k: deposit[k] for k in ('bank_code', 'reference_last4', 'deposit_type',
                                                  'issue_date', 'maturity_date', 'deposited_on')},
                        'amount_paise': 350000000 if sample['bank'] == 'MATCH' else 100000000, 'status': 'ACTIVE'})
                response.raise_for_status()
            current = get(maker, f"deposits/{deposit['id']}")
            command(reviewer, f"deposits/{deposit['id']}/bank-check", {'expected_version': current['version'], 'ledger_id': ledger})
            deadline = time.monotonic() + 60
            while True:
                requests = get(reviewer, 'integration-requests', params={'deposit_id': deposit['id']})
                if requests and requests[0]['state'] == 'SUCCEEDED':
                    assert requests[0]['result']['outcome'] == sample['bank']
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError('Real sandbox/worker exchange did not finish')
                time.sleep(0.5)
    started = time.perf_counter()
    command(reviewer, 'operations/scan', {'institution_id': institution['id']})
    scan_seconds = time.perf_counter() - started
    measurements = {'scripted_per_record_proxy': [], 'consolidated_report': []}
    observations = {}
    for _ in range(5):
        started = time.perf_counter()
        observed = set()
        for _, identity in identities:
            detail = get(reviewer, 'deposits/' + identity)
            if not any(d['active'] and d['category'] == 'DEPOSIT_PROOF' and d['status'] == 'READY'
                       for d in detail['documents']):
                observed.add((identity, 'MISSING_DOCUMENTS'))
            requests = get(reviewer, 'integration-requests', params={'deposit_id': identity})
            if requests and (requests[0]['state'] != 'SUCCEEDED' or requests[0]['result']['outcome'] != 'MATCH'):
                observed.add((identity, 'PENDING_VERIFICATION'))
        measurements['scripted_per_record_proxy'].append(time.perf_counter() - started)
        observations['scripted_per_record_proxy'] = observed
        started = time.perf_counter()
        report = get(reviewer, 'reports/interventions', params={'institution_id': institution['id'], 'limit': 100})
        assert not report['next_cursor']
        observations['consolidated_report'] = {(t['deposit_id'], t['category']) for t in report['items']
            if t['category'] in ('MISSING_DOCUMENTS', 'PENDING_VERIFICATION')}
        measurements['consolidated_report'].append(time.perf_counter() - started)
    results = {}
    for strategy, observed in observations.items():
        tp, fp, fn = len(observed & labels), len(observed - labels), len(labels - observed)
        results[strategy] = {'true_positive': tp, 'false_positive': fp, 'false_negative': fn,
            'median_seconds': round(statistics.median(measurements[strategy]), 4),
            'http_reads_per_iteration': len(identities) * 2 if strategy == 'scripted_per_record_proxy' else 1}
        if fp or fn:
            raise AssertionError(f'{strategy} disagrees with independent fixed labels: FP={fp}, FN={fn}')
    for client in clients.values():
        client.close()
    return {'mode': 'SYNTHETIC_CONTROLLED_PROXY_NOT_HUMAN_BASELINE', 'institution_id': institution['id'],
        'label_version': truth['version'], 'cases': len(identities), 'expected_findings': len(labels), 'iterations': 5,
        'actual_monitor_scan_seconds': round(scan_seconds, 4), 'results': results,
        'limits': truth['limits'], 'reproducible_command': 'python scripts/local.py scripts/benchmark_workflow.py'}


if __name__ == '__main__':
    print(json.dumps(benchmark(), indent=2))
