"""Seed 1000 synthetic test institutions, then measure a real loopback HTTP API."""
import asyncio
import hashlib
import hmac
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from uuid import uuid4

import httpx
from sentinel.compliance import POLICY_REVISION
from sentinel.config import settings
from sentinel.db import session_factory
from sentinel.models import AuditEvent, Deposit, Institution, Obligation, RoleBinding, uid
from sqlalchemy.engine import make_url


def seed_load():
    config = settings()
    if make_url(config.database_url).database != 'sentinel_test':
        raise RuntimeError('Load fixture writes are restricted to sentinel_test')
    subject = '10000000-0000-0000-0000-000000000001'
    run_id = uuid4().hex[:8]
    context = {'academic_year': '2026-27', 'governance': 'PRIVATE', 'programme': 'ENGINEERING',
               'level': 'UG', 'land': 'OWNED', 'exceptional_context': False}
    with session_factory()() as db:
        institutions, obligations, deposits, bindings, audits = [], [], [], [], []
        for index in range(1000):
            institution_id, obligation_id, deposit_id = uid(), uid(), uid()
            institutions.append(Institution(id=institution_id, external_id=f'SYN-LOAD-{run_id}-{index}',
                legal_name=f'Synthetic load institution {run_id} {index}', context=context, owner=subject))
            bindings.append(RoleBinding(subject=subject, role='MAKER', scope_type='INSTITUTION', scope_id=institution_id))
            obligations.append(Obligation(id=obligation_id, institution_id=institution_id, regulatory_event='NEW_INSTITUTION',
                context=context, policy_revision=POLICY_REVISION, required_amount_paise=350000000))
            reference = f'SYN-LOAD-{run_id}-{index}'
            deposits.append(Deposit(id=deposit_id, institution_id=institution_id, obligation_id=obligation_id,
                deposit_type='FDR', bank_code='SYN-LOAD', reference_last4=reference[-4:],
                reference_digest=hmac.new(config.reference_hmac_key.encode(), reference.encode(), hashlib.sha256).hexdigest(),
                hmac_version=config.reference_hmac_version, amount_paise=350000000,
                issue_date=date(2026, 10, 1), maturity_date=date(2036, 10, 1), maker=subject))
            audits.append(AuditEvent(institution_id=institution_id, actor='qualification-harness',
                action='SYNTHETIC_LOAD_FIXTURE', aggregate_id=deposit_id,
                detail={'not_bank_confirmed': True, 'run': run_id}, request_id=run_id))
        db.add_all(institutions)
        db.flush()
        db.add_all(obligations)
        db.flush()
        db.add_all(deposits)
        db.flush()
        db.add_all(bindings + audits)
        db.commit()
    return run_id


async def requests(token):
    semaphore = asyncio.Semaphore(8)
    results = []
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8002/api/v1', timeout=30,
                                 headers={'Authorization': 'Bearer ' + token}) as client:
        async def one(index):
            async with semaphore:
                started = time.perf_counter()
                path = '/dashboard/summary' if index % 2 else '/search/deposits?limit=50'
                response = await client.get(path)
                results.append((response.status_code, time.perf_counter() - started))
        started = time.perf_counter()
        await asyncio.gather(*(one(index) for index in range(200)))
        elapsed = time.perf_counter() - started
    timings = sorted(t for _, t in results)
    return {'requests': len(results), 'concurrency': 8, 'http_failures': sum(status != 200 for status, _ in results),
            'elapsed_seconds': round(elapsed, 3), 'requests_per_second': round(len(results) / elapsed, 2),
            'median_ms': round(statistics.median(timings) * 1000, 2),
            'p95_ms': round(timings[int(len(timings) * .95) - 1] * 1000, 2)}


def main():
    run_id = seed_load()
    environment = dict(os.environ)
    url = make_url(settings().database_url).set(username='sentinel_runtime', password=os.environ['RUNTIME_DB_PASSWORD'])
    environment['DATABASE_URL'] = url.render_as_string(hide_password=False)
    environment['AI_ASSIST_ENABLED'] = 'false'
    target = Path(__file__).resolve().parents[1] / '.local'
    target.mkdir(exist_ok=True)
    with (target / 'load-server.log').open('w', encoding='utf-8') as logfile:
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'sentinel.main:app', '--host', '127.0.0.1',
            '--port', '8002', '--no-access-log'], env=environment, stdout=logfile, stderr=logfile,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            for attempt in range(30):
                try:
                    if httpx.get('http://127.0.0.1:8002/api/v1/health/live', timeout=1).status_code == 200:
                        break
                except Exception:
                    pass
                time.sleep(1)
            else:
                raise RuntimeError('Isolated load API did not start')
            token = httpx.post(os.environ['TEST_OIDC_URL'], data={'client_id': 'sentinel-tests',
                'grant_type': 'password', 'username': 'institution', 'password': os.environ['DEMO_INSTITUTION_PASSWORD']},
                timeout=10).json()['access_token']
            result = asyncio.run(requests(token))
            result.update(mode='LOCAL_SYNTHETIC_LOAD', seeded_institutions=1000, seeded_deposits=1000,
                          fixture_run=run_id, runtime_db_role='sentinel_runtime',
                          limits='One API process, loopback HTTP, real PostgreSQL/OIDC; read-only requests; not production capacity or document throughput')
            print(json.dumps(result, indent=2))
            assert result['http_failures'] == 0, 'Load requests failed'
        finally:
            server.terminate()
            server.wait(timeout=15)


if __name__ == '__main__':
    main()
