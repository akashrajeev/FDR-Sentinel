import os
import time
from uuid import uuid4

import httpx
import pytest
from conftest import post
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


def test_runtime_cannot_modify_history_ddl_or_grant_officer_scopes(clients):
    from sentinel.config import settings
    url = make_url(settings().database_url).set(username='sentinel_runtime', password=os.environ['RUNTIME_DB_PASSWORD'])
    runtime = create_engine(url)
    with runtime.connect() as connection:
        assert connection.scalar(text('SELECT current_user')) == 'sentinel_runtime'
        assert connection.scalar(text('SELECT count(*) FROM audit_events')) > 0
        for statement in ('UPDATE audit_events SET action = action', 'DELETE FROM audit_events',
                          'CREATE TABLE forbidden_probe (id int)', 'UPDATE role_bindings SET enabled = false'):
            with pytest.raises(DBAPIError):
                connection.execute(text(statement))
                connection.commit()
            connection.rollback()
        with pytest.raises(DBAPIError):
            connection.execute(text("INSERT INTO role_bindings (id,subject,role,scope_type,scope_id,enabled,valid_from) "
                "VALUES (:id,:subject,'APPROVER','CASE',:case,true,now())"),
                {'id': str(uuid4()), 'subject': '10000000-0000-0000-0000-000000000001', 'case': str(uuid4())})
            connection.commit()
        connection.rollback()
    runtime.dispose()


def test_actual_keycloak_wrong_audience_and_expiry(clients):
    base = os.environ['TEST_OIDC_URL'].split('/realms/')[0]
    admin_response = httpx.post(base + '/realms/master/protocol/openid-connect/token', data={
        'grant_type': 'password', 'client_id': 'admin-cli', 'username': 'local-admin',
        'password': os.environ['KEYCLOAK_ADMIN_PASSWORD']}, timeout=20)
    assert admin_response.status_code == 200
    headers = {'Authorization': 'Bearer ' + admin_response.json()['access_token']}
    client_id = 'negative-token-' + uuid4().hex
    endpoint = base + '/admin/realms/sentinel/clients'
    created = httpx.post(endpoint, headers=headers, timeout=20, json={
        'clientId': client_id, 'publicClient': True, 'enabled': True, 'standardFlowEnabled': False,
        'directAccessGrantsEnabled': True, 'attributes': {'access.token.lifespan': '1'}})
    assert created.status_code == 201
    location = created.headers['location']
    resource_id = location.rstrip('/').split('/')[-1]
    try:
        data = {'grant_type': 'password', 'client_id': client_id, 'username': 'institution',
                'password': os.environ['DEMO_INSTITUTION_PASSWORD']}
        token = httpx.post(os.environ['TEST_OIDC_URL'], data=data, timeout=20).json()['access_token']
        from fastapi.testclient import TestClient
        from sentinel.main import app
        api = TestClient(app)
        assert api.get('/api/v1/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401
        # Give this isolated test client the actual API audience, then let a real signed token expire.
        updated = httpx.put(endpoint + '/' + resource_id, headers=headers, timeout=20, json={
            'id': resource_id, 'clientId': client_id, 'publicClient': True, 'enabled': True,
            'directAccessGrantsEnabled': True, 'attributes': {'access.token.lifespan': '1'},
            'protocolMappers': [{'name': 'test-audience', 'protocol': 'openid-connect',
                'protocolMapper': 'oidc-audience-mapper', 'config': {'included.client.audience': 'sentinel-api',
                'access.token.claim': 'true', 'id.token.claim': 'false'}}]})
        assert updated.status_code == 204
        token = httpx.post(os.environ['TEST_OIDC_URL'], data=data, timeout=20).json()['access_token']
        time.sleep(2)
        assert api.get('/api/v1/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401
    finally:
        httpx.delete(endpoint + '/' + resource_id, headers=headers, timeout=20)


def test_sensitive_input_validation(clients):
    client = clients()
    body = {'obligation_id': '30000000-0000-0000-0000-000000000001', 'deposit_type': 'FDR',
            'bank_code': 'SYNTHETIC', 'reference': 'SYN-' + uuid4().hex, 'amount_paise': 350000000,
            'issue_date': '2016-01-01', 'maturity_date': '2026-01-01'}
    for amount in (0, -1, 1.5, '350000000', True):
        assert post(client, '/deposits', {**body, 'amount_paise': amount}).status_code == 422
    assert post(client, '/deposits', {**body, 'maturity_date': '2015-01-01'}).status_code == 422
    assert post(client, '/deposits', {**body, 'workflow': 'ACCEPTED'}).status_code == 422


def test_decision_endpoints_require_configured_mfa_before_mutation(clients, monkeypatch):
    from sentinel.config import settings
    from test_lifecycle import prepared_case
    deposit, case = prepared_case(clients)
    config = settings()
    monkeypatch.setattr(config, 'decision_mfa_required', True)
    for username, command in (('approver', 'approve'), ('issuer', 'issue-document')):
        payload = {'expected_version': case['version']}
        if command == 'approve':
            payload.update(regulatory_basis='Synthetic manual review of provisional policy and evidence.',
                           synthetic_acknowledgement=True)
        result = post(clients(username), f"/release-cases/{case['id']}/{command}", payload)
        assert result.status_code == 403, result.text
        assert 'MFA' in result.json()['detail']
    assert clients().get('/api/v1/release-cases/' + case['id']).json()['state'] == case['state']
