import os
import subprocess
import sys
from uuid import uuid4

import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


@pytest.fixture(scope='session')
def services_ready():
    if os.getenv('TEST_SERVICES') != '1':
        pytest.skip('Integration services require scripts/local.py --test or Compose test service')
    from sentinel.config import settings
    url = make_url(settings().database_url)
    if url.database != 'sentinel_test':
        pytest.fail('Refusing test database other than dedicated sentinel_test')
    owner_engine = create_engine(url.set(database='postgres'), isolation_level='AUTOCOMMIT',
                                 connect_args={'connect_timeout': 5})
    with owner_engine.connect() as connection:
        if not connection.scalar(text("SELECT 1 FROM pg_database WHERE datname = 'sentinel_test'")):
            connection.execute(text('CREATE DATABASE sentinel_test'))
    owner_engine.dispose()
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], check=True)
    from sentinel.db import session_factory
    from sentinel.storage import storage

    from scripts.seed_demo import seed
    if not storage().bucket_exists(settings().s3_bucket):
        storage().make_bucket(settings().s3_bucket)
    with session_factory()() as db:
        seed(db)


@pytest.fixture(scope='session')
def clients(services_ready):
    from sentinel.main import app
    tokens = {}

    def get(name='institution'):
        if name not in tokens:
            key = f'DEMO_{name.upper().replace("-", "_")}_PASSWORD'
            result = httpx.post(os.environ['TEST_OIDC_URL'], data={
                'client_id': 'sentinel-tests', 'grant_type': 'password', 'username': name,
                'password': os.environ[key],
            }, timeout=30)
            assert result.status_code == 200, f'Actual Keycloak authentication failed: {result.status_code}'
            tokens[name] = result.json()['access_token']
        return TestClient(app, headers={'Authorization': 'Bearer ' + tokens[name]})
    return get


def post(client, path, body=None, key=None, **kwargs):
    return client.post('/api/v1' + path, json=body,
                       headers={'Idempotency-Key': key or str(uuid4())}, **kwargs)


def pdf_bytes(amount=350000000, issue='2016-10-01', maturity='2026-10-01'):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((55, 65), 'SYNTHETIC BANK - FIXED DEPOSIT RECEIPT', fontsize=18)
    page.insert_text((55, 100), 'DEMO ONLY - NO FINANCIAL VALUE - NOT BANK VERIFIED', fontsize=11)
    page.insert_text((55, 150), f'Amount paise: {amount}\nIssue date: {issue}\nMaturity date: {maturity}',
                     fontsize=12)
    data = pdf.tobytes()
    pdf.close()
    return data


def create_deposit(client, amount=350000000, kind='FDR'):
    payload = {'obligation_id': '30000000-0000-0000-0000-000000000001', 'deposit_type': kind,
               'bank_code': 'SYNTHETIC-BANK', 'reference': 'SYN-' + uuid4().hex, 'amount_paise': amount}
    if kind == 'FDR':
        payload.update(issue_date='2016-10-01', maturity_date='2026-10-01')
    else:
        payload['deposited_on'] = '2026-10-01'
    result = post(client, '/deposits', payload)
    assert result.status_code == 200, result.text
    return result.json()


def upload_and_process(client, deposit, amount=350000000, supersedes=None):
    data = {'category': 'DEPOSIT_PROOF'}
    if supersedes:
        data['supersedes_id'] = supersedes
    result = client.post(f"/api/v1/deposits/{deposit['id']}/documents", data=data,
                         files={'file': ('proof.pdf', pdf_bytes(amount), 'application/pdf')},
                         headers={'Idempotency-Key': str(uuid4())})
    assert result.status_code == 200, result.text
    from sentinel.db import session_factory
    from sentinel.jobs import process_document
    from sentinel.models import Outbox
    from sqlalchemy import select
    with session_factory()() as db:
        event_id = db.scalar(select(Outbox.id).where(Outbox.aggregate_id == result.json()['id']))
    assert process_document.run(event_id) == 'READY'
    return result.json()


def latest(client, deposit):
    return client.get('/api/v1/deposits/' + deposit['id']).json()


def evaluate_submit(client, deposit):
    current = latest(client, deposit)
    result = post(client, f"/deposits/{deposit['id']}/evaluate", {'expected_version': current['version']})
    assert result.status_code == 200, result.text
    current = latest(client, deposit)
    result = post(client, f"/deposits/{deposit['id']}/submit", {'expected_version': current['version']})
    assert result.status_code == 200, result.text
    return result.json()
