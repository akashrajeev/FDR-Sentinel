from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import jwt
import pytest
from conftest import create_deposit, evaluate_submit, latest, pdf_bytes, post, upload_and_process
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


def test_real_oidc_auth_and_forgery(clients):
    from sentinel.main import app
    assert clients().get('/api/v1/me').status_code == 200
    assert TestClient(app).get('/api/v1/me').status_code == 401
    forged = jwt.encode({'sub': 'admin', 'aud': 'sentinel-api'}, 'not-a-real-key', algorithm='HS256')
    assert TestClient(app).get('/api/v1/me', headers={'Authorization': 'Bearer ' + forged}).status_code == 401


def test_onboard_and_tenant_scope(clients):
    a, b = clients(), clients('other-institution')
    context = {'academic_year': '2026-27', 'governance': 'PRIVATE', 'programme': 'ENGINEERING_UG',
               'land': 'OWNED', 'exceptional_context': False}
    result = post(b, '/institutions', {'external_id': 'SYN-' + uuid4().hex, 'legal_name': 'Synthetic B',
                                      'context': context})
    assert result.status_code == 200
    institution = result.json()
    assert a.get('/api/v1/institutions/' + institution['id']).status_code == 404
    assert post(a, '/obligations', {'institution_id': institution['id'],
                                  'regulatory_event': 'NEW_INSTITUTION'}).status_code == 404
    assert post(b, '/obligations', {'institution_id': institution['id'],
                                  'regulatory_event': 'HISTORICAL_RECORD'}).status_code == 200


@pytest.mark.parametrize('kind', ['RTGS', 'ONLINE', 'RPGF', 'OTHER_LEGACY'])
def test_non_fdr_without_fabricated_dates(clients, kind):
    result = create_deposit(clients(), kind=kind)
    assert result['maturity_date'] is None and result['issue_date'] is None
    assert result['workflow'] == 'DRAFT'


def test_idempotency_and_reference_privacy(clients):
    client = clients()
    body = {'obligation_id': '30000000-0000-0000-0000-000000000001', 'deposit_type': 'FDR',
            'bank_code': 'SYN-BANK', 'reference': 'SYNTHETIC-' + uuid4().hex, 'amount_paise': 350000000,
            'issue_date': '2016-01-01', 'maturity_date': '2026-01-01'}
    key = str(uuid4())
    first = post(client, '/deposits', body, key)
    assert first.status_code == 200
    assert 'reference_digest' not in first.text and body['reference'] not in first.text
    assert post(client, '/deposits', body, key).json() == first.json()
    assert post(client, '/deposits', {**body, 'amount_paise': 10}, key).status_code == 409
    assert post(client, '/deposits', body).status_code == 409


def test_e1_deficient_scrutiny_return_correction_acceptance(clients):
    maker, officer = clients(), clients('reviewer')
    deposit = create_deposit(maker, amount=1000000)
    original = upload_and_process(maker, deposit, amount=1000000)
    submitted = evaluate_submit(maker, deposit)
    assert submitted['workflow'] == 'PENDING_SCRUTINY'
    assert latest(maker, deposit)['evaluations'][0]['result']['outcome'] == 'FAIL'
    decision = {'expected_version': submitted['version'], 'decision': 'ACCEPT_REGISTRATION',
                'reason': 'Synthetic officer evidence review', 'evidence_reviewed': True}
    assert post(officer, f"/deposits/{deposit['id']}/review", decision).status_code == 409
    decision['decision'] = 'RETURN'
    result = post(officer, f"/deposits/{deposit['id']}/review", decision)
    assert result.status_code == 200
    corrected = post(maker, f"/deposits/{deposit['id']}/correct", {
        'expected_version': result.json()['version'], 'amount_paise': 350000000,
        'issue_date': '2016-10-01', 'maturity_date': '2026-10-01'})
    assert corrected.status_code == 200
    upload_and_process(maker, deposit, supersedes=original['id'])
    submitted = evaluate_submit(maker, deposit)
    result = post(officer, f"/deposits/{deposit['id']}/review", {
        **decision, 'decision': 'ACCEPT_REGISTRATION', 'expected_version': submitted['version']})
    assert result.status_code == 200, result.text
    assert result.json()['verification_status'] == 'MANUALLY_REVIEWED'
    assert result.json()['lifecycle_status'] != 'RELEASED'
    assert len(latest(maker, deposit)['documents']) == 2


def test_e3_document_change_invalidates_evaluation(clients):
    client = clients()
    deposit = create_deposit(client)
    original = upload_and_process(client, deposit)
    result = post(client, f"/deposits/{deposit['id']}/evaluate", {'expected_version': latest(client, deposit)['version']})
    assert result.status_code == 200
    revision = result.json()['input_revision']
    upload_and_process(client, deposit, supersedes=original['id'])
    current = latest(client, deposit)
    assert current['input_revision'] > revision
    assert post(client, f"/deposits/{deposit['id']}/submit", {'expected_version': current['version']}).status_code == 409


def test_private_upload_replay_and_cross_tenant_download(clients):
    maker, outsider = clients(), clients('other-institution')
    deposit = create_deposit(maker)
    path = f"/api/v1/deposits/{deposit['id']}/documents"
    key = str(uuid4())
    kwargs = {'files': {'file': ('first.pdf', pdf_bytes(), 'application/pdf')},
              'headers': {'Idempotency-Key': key}}
    first = maker.post(path, **kwargs)
    assert first.status_code == 200
    assert maker.post(path, **kwargs).json() == first.json()
    assert outsider.get(f"/api/v1/documents/{first.json()['id']}/content").status_code == 404
    assert maker.get(f"/api/v1/documents/{first.json()['id']}/content").status_code == 409
    bad = maker.post(path, files={'file': ('fake.pdf', b'not pdf', 'application/pdf')},
                     headers={'Idempotency-Key': str(uuid4())})
    assert bad.status_code == 422
    assert outsider.get('/api/v1/deposits/' + deposit['id']).status_code == 404


def test_e6_concurrent_stale_evaluations(clients):
    maker = clients()
    deposit = create_deposit(maker)
    upload_and_process(maker, deposit)
    current = latest(maker, deposit)
    def action(_):
        return post(clients(), f"/deposits/{deposit['id']}/evaluate", {'expected_version': current['version']}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(action, range(2)))
    assert sorted(results) == [200, 409]


def test_role_denial_and_maker_checker(clients):
    from sentinel.db import session_factory
    from sentinel.models import RoleBinding
    maker = clients()
    deposit = create_deposit(maker)
    upload_and_process(maker, deposit)
    submitted = evaluate_submit(maker, deposit)
    body = {'expected_version': submitted['version'], 'decision': 'ACCEPT_REGISTRATION',
            'reason': 'Synthetic evidence reviewed', 'evidence_reviewed': True}
    assert post(maker, f"/deposits/{deposit['id']}/review", body).status_code == 403
    with session_factory()() as db:
        binding = RoleBinding(subject='10000000-0000-0000-0000-000000000001', role='REVIEWER',
                              scope_type='INSTITUTION', scope_id=deposit['institution_id'])
        db.add(binding)
        db.commit()
        binding_id = binding.id
    try:
        assert post(maker, f"/deposits/{deposit['id']}/review", body).status_code == 403
    finally:
        with session_factory()() as db:
            db.delete(db.get(RoleBinding, binding_id))
            db.commit()
    assert post(clients('auditor'), f"/deposits/{deposit['id']}/evaluate",
                {'expected_version': submitted['version']}).status_code == 403


def test_audit_immutable_and_scoped(clients):
    from sentinel.db import session_factory
    from sentinel.models import AuditEvent
    events = clients().get('/api/v1/audit-events').json()
    assert events
    with session_factory()() as db:
        event = db.scalar(select(AuditEvent).limit(1))
        with pytest.raises(DBAPIError):
            db.execute(text('UPDATE audit_events SET action = :action WHERE id = :id'),
                       {'action': 'FORGED', 'id': event.id})
            db.commit()
        db.rollback()


def test_scanner_real_eicar_and_pipeline_outage(clients, monkeypatch):
    from sentinel.storage import scan_bytes
    # Standard antivirus test string, not executable malware.
    eicar = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
    assert scan_bytes(eicar) == 'INFECTED'
    from sentinel.db import session_factory
    from sentinel.jobs import process_document
    from sentinel.models import Outbox
    maker = clients()
    deposit = create_deposit(maker)
    result = maker.post(f"/api/v1/deposits/{deposit['id']}/documents", files={
        'file': ('test.pdf', pdf_bytes(), 'application/pdf')}, headers={'Idempotency-Key': str(uuid4())})
    assert result.status_code == 200
    with session_factory()() as db:
        event = db.scalar(select(Outbox).where(Outbox.aggregate_id == result.json()['id']))
        event_id = event.id
    def outage(_):
        raise ConnectionError('Injected scanner outage')
    monkeypatch.setattr('sentinel.jobs.scan_bytes', outage)
    with pytest.raises(Exception):
        process_document.run(event_id)
    current = latest(maker, deposit)
    assert current['documents'][0]['status'] == 'FAILED'
    assert maker.get(f"/api/v1/documents/{result.json()['id']}/content").status_code == 409
