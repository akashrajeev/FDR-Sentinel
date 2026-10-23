"""Actual local service outages, with unconditional recovery; synthetic intake only."""
import json
import os
import subprocess
import time
from uuid import uuid4

import httpx
from sentinel.synthetic import fixture_pdf

ROOT = 'http://localhost:8088/api/v1'


def service(action, name):
    subprocess.run(['docker', 'compose', action, name], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE, timeout=60)


def wait_for(client, path, predicate, timeout=100):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(ROOT + path)
        if response.status_code == 200 and predicate(response.json()):
            return response.json()
        time.sleep(2)
    raise RuntimeError('Recovery condition timed out')


def main():
    token = httpx.post('http://localhost:8081/realms/sentinel/protocol/openid-connect/token', data={
        'client_id': 'sentinel-tests', 'grant_type': 'password', 'username': 'institution',
        'password': os.environ['DEMO_INSTITUTION_PASSWORD']}, timeout=15).json()['access_token']
    client = httpx.Client(headers={'Authorization': 'Bearer ' + token}, timeout=20)
    results = []
    for dependency in ('redis', 'clamav'):
        deposited = client.post(ROOT + '/deposits', headers={'Idempotency-Key': str(uuid4())}, json={
            'obligation_id': '30000000-0000-0000-0000-000000000001', 'deposit_type': 'FDR',
            'bank_code': 'SYN-OUTAGE', 'reference': 'SYN-' + uuid4().hex, 'amount_paise': 350000000,
            'issue_date': '2016-10-01', 'maturity_date': '2026-10-01'})
        deposited.raise_for_status()
        deposit = deposited.json()
        started = time.monotonic()
        try:
            print('Stopping ' + dependency + ' for the synthetic outage check.', flush=True)
            service('stop', dependency)
            health = client.get(ROOT + '/health/ready').json()
            assert health['status'] == 'degraded_intake_available', health
            uploaded = client.post(ROOT + f"/deposits/{deposit['id']}/documents",
                headers={'Idempotency-Key': str(uuid4())}, files={
                    'file': ('synthetic.pdf', fixture_pdf('digital-a'), 'application/pdf')})
            uploaded.raise_for_status()
            document_id = uploaded.json()['id']
            trace_id = uploaded.headers['x-trace-id']
            if dependency == 'clamav':
                unavailable = wait_for(client, f"/deposits/{deposit['id']}",
                                      lambda d: d['documents'][0]['status'] == 'FAILED', timeout=35)
                assert unavailable['workflow'] == 'DRAFT'
            assert client.get(ROOT + f'/documents/{document_id}/content').status_code == 409
            assert client.get(ROOT + f"/deposits/{deposit['id']}").json()['workflow'] == 'DRAFT'
        finally:
            print('Restarting ' + dependency + '.', flush=True)
            service('start', dependency)
        recovered = wait_for(client, f"/deposits/{deposit['id']}",
                             lambda d: d['documents'][0]['status'] == 'READY', timeout=130)
        # Actual broker/worker correlation, separate from eager task unit instrumentation.
        logs = subprocess.run(['docker', 'compose', 'logs', '--since', '10m', 'worker'],
                              check=True, capture_output=True, text=True, timeout=20).stdout
        correlated = any(trace_id in line and 'document.process' in line for line in logs.splitlines())
        assert correlated, 'Upload trace did not reach the real worker'
        results.append({'dependency': dependency, 'degraded_intake': True, 'unsafe_read_denied': True,
                        'real_worker_trace_correlated': correlated,
                        'recovered_document_id': document_id, 'document_rows': len(recovered['documents']),
                        'elapsed_seconds': round(time.monotonic() - started, 2),
                        'workflow_after_recovery': recovered['workflow']})
    print(json.dumps({'mode': 'ACTUAL_LOCAL_OUTAGE_SYNTHETIC_DATA', 'results': results}, indent=2), flush=True)
    client.close()


if __name__ == '__main__':
    main()
