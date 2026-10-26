import os
import time
from uuid import uuid4

import httpx
import pytest
from conftest import create_deposit, latest, post
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


def fixture_ledger(deposit, status='ACTIVE'):
    from sentinel.config import settings
    identity = 'SB-' + uuid4().hex
    response = httpx.post(settings().sandbox_url + '/v1/fixtures/ledger', timeout=10,
        headers={'Authorization': 'Bearer ' + os.environ['SANDBOX_ADMIN_KEY']}, json={
            'id': identity, 'institution_external_id': 'SYNTHETIC-001',
            'bank_code': deposit['bank_code'], 'reference_last4': deposit['reference_last4'],
            'deposit_type': deposit['deposit_type'], 'amount_paise': deposit['amount_paise'],
            'issue_date': deposit['issue_date'], 'maturity_date': deposit['maturity_date'],
            'deposited_on': deposit['deposited_on'], 'status': status})
    assert response.status_code == 200, response.text
    return identity


def run_request(identity, timeout=25):
    from sentinel.db import session_factory
    from sentinel.integrations import process_one
    from sentinel.models import IntegrationRequest
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = process_one(identity)
        with session_factory()() as db:
            record = db.get(IntegrationRequest, identity)
            result = record.result
        if state in ('SUCCEEDED', 'STALE', 'DEAD_LETTER'):
            return state, result
        time.sleep(1)
    raise AssertionError('Actual sandbox exchange timed out')


def bank_request(clients, deposit, ledger, behavior='NORMAL', key=None):
    return post(clients('reviewer'), f"/deposits/{deposit['id']}/bank-check", {
        'expected_version': latest(clients(), deposit)['version'], 'ledger_id': ledger, 'behavior': behavior}, key=key)


def test_independent_ledger_actual_http_signed_match_and_mismatch(clients):
    deposit = create_deposit(clients())
    ledger = fixture_ledger(deposit)
    requested = bank_request(clients, deposit, ledger)
    assert requested.status_code == 200, requested.text
    state, result = run_request(requested.json()['id'])
    assert state == 'SUCCEEDED' and result['outcome'] == 'MATCH'
    assert latest(clients(), deposit)['verification_status'] == 'INSTITUTION_DECLARED'
    # A separately persisted ledger value is not changed to match a later declaration.
    correction = post(clients(), f"/deposits/{deposit['id']}/correct", {
        'expected_version': latest(clients(), deposit)['version'], 'amount_paise': 400000000,
        'issue_date': deposit['issue_date'], 'maturity_date': deposit['maturity_date']})
    assert correction.status_code == 200
    requested = bank_request(clients, deposit, ledger)
    _, result = run_request(requested.json()['id'])
    assert result['outcome'] == 'MISMATCH' and result['observed']['amount_paise'] == 350000000
    from sentinel.db import session_factory
    from sentinel.integrations import result_blockers
    from sentinel.models import Deposit
    with session_factory()() as db:
        assert any('MISMATCH' in b for b in result_blockers(db, db.get(Deposit, deposit['id'])))


@pytest.mark.parametrize('behavior', ['DELAYED', 'TRANSIENT_FAILURE'])
def test_pending_and_recoverable_http_failure(clients, behavior):
    deposit = create_deposit(clients())
    response = bank_request(clients, deposit, fixture_ledger(deposit), behavior)
    from sentinel.integrations import process_one
    assert process_one(response.json()['id']) == 'WAITING'
    assert run_request(response.json()['id'])[1]['outcome'] == 'MATCH'


def test_stale_result_and_scope_denial(clients):
    deposit = create_deposit(clients())
    response = bank_request(clients, deposit, fixture_ledger(deposit))
    assert post(clients('other-institution'), f"/deposits/{deposit['id']}/bank-check", {
        'expected_version': 1, 'ledger_id': 'SB-FDR-001'}).status_code == 404
    assert post(clients(), f"/deposits/{deposit['id']}/bank-check", {
        'expected_version': 1, 'ledger_id': 'SB-FDR-001'}).status_code == 403
    assert post(clients(), f"/deposits/{deposit['id']}/correct", {
        'expected_version': latest(clients(), deposit)['version'], 'amount_paise': 400000000,
        'issue_date': deposit['issue_date'], 'maturity_date': deposit['maturity_date']}).status_code == 200
    assert run_request(response.json()['id'])[0] == 'STALE'


def test_registry_actual_independent_source_and_authentication(clients):
    institution = '20000000-0000-0000-0000-000000000001'
    result = post(clients(), f'/institutions/{institution}/registry-check', {})
    assert result.status_code == 200
    state, result = run_request(result.json()['id'])
    assert state == 'SUCCEEDED' and result['outcome'] == 'MATCH'
    assert clients().get('/api/v1/institutions/' + institution).json()['registry_status'] == 'SANDBOX_MATCH'
    from sentinel.config import settings
    assert httpx.get(settings().sandbox_url + '/v1/catalogue', timeout=5).status_code == 401
    assert httpx.post(settings().sandbox_url + '/v1/fixtures/ledger', json={},
        headers={'Authorization': 'Bearer ' + settings().sandbox_api_key}, timeout=5).status_code == 403


def test_signature_correlation_and_replay_are_checked(clients):
    from sentinel.db import session_factory
    from sentinel.integrations import call_sandbox, verified
    from sentinel.models import IntegrationRequest
    deposit = create_deposit(clients())
    response = bank_request(clients, deposit, fixture_ledger(deposit))
    with session_factory()() as db:
        request = db.get(IntegrationRequest, response.json()['id'])
        envelope = call_sandbox('POST', '/v1/requests', request.payload)
        assert verified(envelope, request)[0]['client_key'] == request.payload['client_key']
        assert call_sandbox('POST', '/v1/requests', request.payload)['payload']['remote_id'] == envelope['payload']['remote_id']
        envelope['payload']['client_key'] = 'forged-correlation'
        with pytest.raises(ValueError):
            verified(envelope, request)
    assert run_request(response.json()['id'])[0] == 'SUCCEEDED'


def test_database_roles_isolate_external_records(clients):
    from sentinel.config import settings
    url = make_url(settings().database_url)
    for username, password, statement in (
        ('sentinel_runtime', os.environ['RUNTIME_DB_PASSWORD'], 'SELECT * FROM sandbox.ledger'),
        ('sentinel_sandbox', os.environ['SANDBOX_DB_PASSWORD'], 'SELECT * FROM public.deposit_records')):
        engine = create_engine(url.set(username=username, password=password))
        with engine.connect() as connection, pytest.raises(DBAPIError):
            connection.execute(text(statement))
        engine.dispose()


def test_release_reconciliation_requires_human_issued_output(clients):
    from test_lifecycle import approve_body, clear, prepared_case
    deposit, case = prepared_case(clients)
    ledger = fixture_ledger(deposit)
    assert post(clients('issuer'), f"/release-cases/{case['id']}/sandbox-exchange", {
        'expected_version': case['version'], 'ledger_id': ledger}).status_code == 409
    for bureau, user in [('PGRC', 'pgrc'), ('VIGILANCE', 'vigilance'), ('GRANTS', 'reviewer')]:
        case = clear(clients, case, bureau, user)
    case = post(clients('approver'), f"/release-cases/{case['id']}/approve", approve_body(case)).json()
    issued = post(clients('issuer'), f"/release-cases/{case['id']}/issue-document", {'expected_version': case['version']})
    assert issued.status_code == 200
    case = issued.json()
    for ledger_id, outcome in [(None, 'CASE_RECEIVED'), (ledger, 'SANDBOX_COMPLETED')]:
        response = post(clients('issuer'), f"/release-cases/{case['id']}/sandbox-exchange", {
            'expected_version': case['version'], 'ledger_id': ledger_id})
        assert response.status_code == 200, response.text
        assert run_request(response.json()['id'])[1]['outcome'] == outcome
    assert latest(clients(), deposit)['lifecycle_status'] != 'RELEASED'
    assert clients().get('/api/v1/release-cases/' + case['id']).json()['state'] == 'ISSUED_SYNTHETIC'
    from sentinel.db import session_factory
    from sentinel.models import IntegrationRequest
    with session_factory()() as db:
        assert len(list(db.scalars(select(IntegrationRequest).where(IntegrationRequest.case_id == case['id'])))) == 2
