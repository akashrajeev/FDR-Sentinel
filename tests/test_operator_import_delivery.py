import csv
import io
import os
from uuid import uuid4

import httpx
import pytest
from conftest import create_deposit, post
from sqlalchemy import func, select

pytestmark = pytest.mark.integration


def new_institution(clients):
    from scripts.seed_demo import CONTEXT
    response = post(clients(), '/institutions', {'external_id': 'SYNTHETIC-' + uuid4().hex,
        'legal_name': 'Fictional operator acceptance institution', 'context': CONTEXT})
    assert response.status_code == 200, response.text
    return response.json()


def test_operator_assigns_and_revokes_new_institution_scope_without_financial_authority(clients):
    from sentinel.db import session_factory
    from sentinel.models import AuditEvent
    institution = new_institution(clients)
    operator, reviewer = clients('operator'), clients('reviewer')
    body = {'subject': reviewer.get('/api/v1/me').json()['subject'], 'role': 'REVIEWER',
            'scope_type': 'INSTITUTION', 'scope_id': institution['id'],
            'reason': 'Assign independent scrutiny for fictional onboarding.'}
    assert reviewer.get('/api/v1/institutions/' + institution['id']).status_code == 404
    assert post(clients(), '/operator/assignments', body).status_code == 403
    key = str(uuid4())
    response = post(operator, '/operator/assignments', body, key=key)
    assert response.status_code == 200, response.text
    assert post(operator, '/operator/assignments', body, key=key).json() == response.json()
    assert reviewer.get('/api/v1/institutions/' + institution['id']).status_code == 200
    assert operator.get('/api/v1/institutions/' + institution['id']).status_code == 404
    with session_factory()() as db:
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.aggregate_id == response.json()['id'], AuditEvent.action == 'OPERATOR_SCOPE_CHANGED')) == 1
    assert post(operator, '/operator/assignments', {**body, 'enabled': False}).status_code == 200
    assert reviewer.get('/api/v1/institutions/' + institution['id']).status_code == 404
    assert post(operator, '/operator/assignments', {**body,
        'subject': operator.get('/api/v1/me').json()['subject']}).status_code == 403
    assert post(operator, '/operator/assignments', {**body, 'role': 'OPERATOR'}).status_code == 422


def csv_data(rows):
    from sentinel.import_api import HEADERS
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=HEADERS)
    writer.writeheader()
    for row in rows:
        writer.writerow({'obligation_id': '30000000-0000-0000-0000-000000000001', 'deposit_type': 'FDR',
            'bank_code': 'SYN-IMPORT', 'reference': 'SYN-' + uuid4().hex,
            'amount_paise': 350000000, 'issue_date': '2016-10-01', 'maturity_date': '2026-10-01',
            'deposited_on': '', **row})
    return output.getvalue().encode()


def preview(client, data):
    return client.post('/api/v1/legacy-import/preview', files={'file': ('synthetic.csv', data, 'text/csv')})


def commit(client, data, digest, key=None):
    return client.post('/api/v1/legacy-import/commit', files={'file': ('synthetic.csv', data, 'text/csv')},
        data={'expected_sha256': digest}, headers={'Idempotency-Key': key or str(uuid4())})


def test_csv_preview_atomic_commit_and_stable_multipart_replay(clients):
    data = csv_data([{}, {'deposit_type': 'RTGS', 'issue_date': '', 'maturity_date': '', 'deposited_on': '2016-10-01'}])
    checked = preview(clients(), data)
    assert checked.status_code == 200 and checked.json()['rows'] == 2
    key = str(uuid4())
    response = commit(clients(), data, checked.json()['sha256'], key)
    assert response.status_code == 200, response.text
    assert commit(clients(), data, checked.json()['sha256'], key).json() == response.json()
    assert all(r['workflow'] == 'DRAFT' and r['verification_status'] == 'INSTITUTION_DECLARED'
               for r in response.json()['records'])
    assert response.json()['records'][1]['maturity_date'] is None
    assert commit(clients(), data + b'\n', checked.json()['sha256']).status_code == 409
    assert preview(clients(), data).status_code == 422


def test_invalid_or_cross_scope_import_never_partially_writes(clients):
    from sentinel.db import session_factory
    from sentinel.models import Deposit
    bank = 'SYN-IMPORT-' + uuid4().hex[:8].upper()
    data = csv_data([{'bank_code': bank}, {'bank_code': bank, 'amount_paise': 0}])
    assert preview(clients(), data).status_code == 422
    import hashlib
    assert commit(clients(), data, hashlib.sha256(data).hexdigest()).status_code == 422
    with session_factory()() as db:
        assert db.scalar(select(func.count()).select_from(Deposit).where(Deposit.bank_code == bank)) == 0
    assert preview(clients('other-institution'), csv_data([{}])).status_code == 404
    assert preview(clients('reviewer'), csv_data([{}])).status_code == 403
    assert preview(clients(), b'bad,header\n1,2\n').status_code == 422


def notice(clients):
    from sentinel.db import session_factory
    from sentinel.delivery import ensure_delivery
    from sentinel.models import Notification, NotificationDelivery
    deposit = create_deposit(clients())
    with session_factory()() as db:
        notification = Notification(institution_id=deposit['institution_id'], deposit_id=deposit['id'],
            recipient='10000000-0000-0000-0000-000000000001', kind='MATURITY_IN_APP', dedupe_key='test-' + uuid4().hex,
            detail={'days_remaining': 7, 'threshold': 7, 'as_of': '2026-09-24'})
        db.add(notification)
        db.flush()
        ensure_delivery(db, notification.id)
        identity = db.scalar(select(NotificationDelivery.id).where(NotificationDelivery.notification_id == notification.id))
        db.commit()
        return notification.id, identity


def test_actual_smtp_message_in_mailpit_and_replayed_worker_no_duplicate(clients):
    from sentinel.delivery import deliver_one
    notification, delivery = notice(clients)
    assert deliver_one(delivery) == 'SENT'
    assert deliver_one(delivery) == 'NOOP'
    mailbox = os.environ.get('MAILPIT_URL', 'http://mailpit:8025')
    # Search the unique subject rather than assuming this is among the newest mailbox rows.
    response = httpx.get(mailbox + '/api/v1/search', params={'query': 'subject:' + notification, 'limit': 100}, timeout=10)
    assert response.status_code == 200
    messages = [m for m in response.json()['messages'] if notification in m['Subject']]
    assert len(messages) == 1
    content = httpx.get(mailbox + '/api/v1/message/' + messages[0]['ID'], timeout=10).json()
    assert 'Maturity does not authorize release' in content['Text']


def test_real_smtp_failure_dead_letter_then_authorized_recovery(clients, monkeypatch):
    from sentinel.config import settings
    from sentinel.delivery import deliver_one
    notification, delivery = notice(clients)
    with monkeypatch.context() as patch:
        patch.setattr(settings(), 'smtp_port', 1)  # Actual refused local TCP connection, not a fake success.
        for _ in range(5):
            state = deliver_one(delivery)
        assert state == 'DEAD_LETTER'
    body = {'expected_version': 5}
    assert post(clients(), f'/notifications/{notification}/retry', body).status_code == 403
    assert post(clients('other-institution'), f'/notifications/{notification}/retry', body).status_code == 404
    response = post(clients('reviewer'), f'/notifications/{notification}/retry', body)
    assert response.status_code == 200, response.text
    assert deliver_one(delivery) == 'SENT'
