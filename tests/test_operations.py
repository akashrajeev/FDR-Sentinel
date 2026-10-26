import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from conftest import evaluate_submit, latest, post, upload_and_process
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


def workspace(clients, exceptional=False):
    from scripts.seed_demo import CONTEXT
    maker, reviewer = clients(), clients('reviewer')
    institution = post(maker, '/institutions', {'external_id': 'SYNTHETIC-' + uuid4().hex,
        'legal_name': 'Fictional intervention ' + uuid4().hex[:8],
        'context': {**CONTEXT, 'exceptional_context': exceptional}}).json()
    for username, role in [('reviewer', 'REVIEWER'), ('approver', 'APPROVER'), ('auditor', 'AUDITOR')]:
        response = post(clients('operator'), '/operator/assignments', {
            'subject': clients(username).get('/api/v1/me').json()['subject'], 'role': role,
            'scope_type': 'INSTITUTION', 'scope_id': institution['id'],
            'reason': 'Assign fictional operations acceptance scope.'})
        assert response.status_code == 200, response.text
    obligation = post(maker, '/obligations', {'institution_id': institution['id'],
        'regulatory_event': 'NEW_INSTITUTION'}).json()
    response = post(maker, '/deposits', {'obligation_id': obligation['id'], 'deposit_type': 'FDR',
        'bank_code': 'SYN-OPS', 'reference': 'SYN-' + uuid4().hex, 'amount_paise': 350000000,
        'issue_date': '2016-10-01', 'maturity_date': '2026-10-01'})
    assert response.status_code == 200, response.text
    return institution['id'], response.json(), reviewer


def scan(client, tenant, instant=None, key=None):
    return post(client, '/operations/scan', {'institution_id': tenant,
        'as_of': instant.isoformat() if instant else None}, key=key)


def items(client, tenant, category=None, **params):
    response = client.get('/api/v1/reports/interventions', params={'institution_id': tenant,
        **({'category': category} if category else {}), **params})
    assert response.status_code == 200, response.text
    return response.json()


def configured(client, tenant, **overrides):
    policy = client.get(f'/api/v1/institutions/{tenant}/operations-policy').json()
    return post(client, f'/institutions/{tenant}/operations-policy', {**policy['configuration'],
        'expected_revision': policy['revision'], 'reason': 'Fictional product service-level configuration.', **overrides})


def test_policy_scoped_versioned_idempotent_and_immutable(clients):
    tenant, _, reviewer = workspace(clients)
    path = f'/institutions/{tenant}/operations-policy'
    supervisor = clients('approver').get('/api/v1/me').json()['subject']
    body = {'expected_revision': 0, 'supervisor_subject': supervisor, 'maturity_days': [60, 14],
            'reason': 'Fictional product deadlines reviewed by officer.'}
    assert post(clients(), path, body).status_code == 403
    assert post(clients('other-institution'), path, body).status_code == 404
    key = str(uuid4())
    first = post(reviewer, path, body, key=key)
    assert first.status_code == 200, first.text
    assert post(reviewer, path, body, key=key).json() == first.json()
    assert post(reviewer, path, body).status_code == 409
    assert configured(reviewer, tenant, supervisor_subject=reviewer.get('/api/v1/me').json()['subject']).status_code == 422
    assert configured(reviewer, tenant, supervisor_subject=clients('other-institution').get('/api/v1/me').json()['subject']).status_code == 422
    assert configured(reviewer, tenant, maturity_days=[0]).status_code == 422
    from sentinel.db import engine
    with pytest.raises(DBAPIError), engine().begin() as connection:
        connection.execute(text('UPDATE operations_policies SET revision=99 WHERE institution_id=:id'), {'id': tenant})


def test_missing_evidence_escalates_real_smtp_ack_does_not_resolve_and_source_closes(clients):
    from sentinel.db import session_factory
    from sentinel.delivery import deliver_one
    from sentinel.models import NotificationDelivery, now
    tenant, deposit, reviewer = workspace(clients)
    supervisor = clients('approver').get('/api/v1/me').json()['subject']
    assert configured(reviewer, tenant, missing_document_hours=1, escalation_hours=1,
                      supervisor_subject=supervisor).status_code == 200
    instant = now() + timedelta(hours=3)
    response = scan(reviewer, tenant, instant)
    assert response.status_code == 200, response.text
    task = items(reviewer, tenant, 'MISSING_DOCUMENTS')['items'][0]
    assert task['deposit_id'] == deposit['id']
    path = f"/api/v1/interventions/{task['id']}/notifications"
    notices = reviewer.get(path).json()
    assert len([n for n in notices if n['kind'] == 'OPERATIONS_ESCALATION']) == 1
    assert any(n['recipient'] == supervisor and n['kind'] == 'OPERATIONS_ESCALATION' for n in notices)
    assert scan(reviewer, tenant, instant).json()['notifications'] == 0
    key = str(uuid4())
    acknowledged = post(reviewer, f"/interventions/{task['id']}/acknowledge",
        {'reason': 'Contacted fictional maker to obtain missing evidence.'}, key=key)
    assert acknowledged.status_code == 200
    assert acknowledged.json()['state'] == 'OPEN'
    assert post(reviewer, f"/interventions/{task['id']}/acknowledge",
        {'reason': 'Contacted fictional maker to obtain missing evidence.'}, key=key).json() == acknowledged.json()
    notice = next(n for n in notices if n['kind'] == 'OPERATIONS_ESCALATION')
    with session_factory()() as db:
        delivery = db.scalar(select(NotificationDelivery.id).where(NotificationDelivery.notification_id == notice['id']))
    assert deliver_one(delivery) == 'SENT'
    messages = httpx.get(os.environ.get('MAILPIT_URL', 'http://mailpit:8025') + '/api/v1/search',
                        params={'query': 'subject:' + notice['id'], 'limit': 100}, timeout=10).json()['messages']
    message = next(m for m in messages if notice['id'] in m['Subject'])
    content = httpx.get(os.environ.get('MAILPIT_URL', 'http://mailpit:8025') + '/api/v1/message/' + message['ID'], timeout=10).json()
    assert 'ESCALATION' in content['Text'] and 'not a statutory deadline' in content['Text']
    document = upload_and_process(clients(), deposit)
    assert scan(reviewer, tenant, instant).json()['resolved'] >= 1
    assert items(reviewer, tenant, 'MISSING_DOCUMENTS')['total'] == 0
    assert items(reviewer, tenant, 'MISSING_DOCUMENTS', state='RESOLVED')['items'][0]['acknowledged_by']
    # Superseding evidence can reopen the condition, with retained resolved history.
    from conftest import pdf_bytes
    replacement = clients().post(f"/api/v1/deposits/{deposit['id']}/documents",
        data={'category': 'DEPOSIT_PROOF', 'supersedes_id': document['id']},
        files={'file': ('replacement.pdf', pdf_bytes(), 'application/pdf')},
        headers={'Idempotency-Key': str(uuid4())})
    assert replacement.status_code == 200, replacement.text
    scan(reviewer, tenant, instant)
    reopened = items(reviewer, tenant, 'MISSING_DOCUMENTS')['items'][0]
    assert reopened['id'] != task['id'] and reopened['episode'] == 2
    assert not reopened['acknowledged_by']


def test_scrutiny_discrepancy_and_unknown_context_follow_source_without_authorizing(clients):
    from sentinel.models import now
    tenant, deposit, reviewer = workspace(clients, exceptional=True)
    upload_and_process(clients(), deposit, amount=100000000)
    evaluate_submit(clients(), deposit)
    assert scan(reviewer, tenant, now() + timedelta(days=5)).status_code == 200
    categories = items(reviewer, tenant)['counts']
    assert all(categories[c] for c in ('OFFICER_REVIEW', 'UNRESOLVED_DISCREPANCY', 'REGULATORY_REVIEW'))
    assert latest(clients(), deposit)['workflow'] == 'PENDING_SCRUTINY'
    returned = post(reviewer, f"/deposits/{deposit['id']}/review", {
        'expected_version': latest(clients(), deposit)['version'], 'decision': 'RETURN',
        'reason': 'Fictional evidence differs; return for correction.', 'evidence_reviewed': True})
    assert returned.status_code == 200, returned.text
    scan(reviewer, tenant)
    assert items(reviewer, tenant, 'OFFICER_REVIEW')['total'] == 0
    assert items(reviewer, tenant, 'UNRESOLVED_DISCREPANCY')['total'] > 0


def test_actual_http_registry_and_failed_bank_checks_remain_actionable_until_current_match(clients):
    from sentinel.models import now
    from test_sandbox_integrations import run_request
    tenant, deposit, reviewer = workspace(clients)
    # A missing immutable independent source produces NOT_FOUND, never a fabricated match.
    response = post(reviewer, f"/deposits/{deposit['id']}/bank-check", {'expected_version': deposit['version'],
                    'ledger_id': 'SB-missing-' + uuid4().hex, 'behavior': 'NORMAL'})
    assert run_request(response.json()['id'])[1]['outcome'] == 'NOT_FOUND'
    registry = post(clients(), f'/institutions/{tenant}/registry-check', {})
    assert run_request(registry.json()['id'])[1]['outcome'] == 'NOT_FOUND'
    assert scan(reviewer, tenant, now() + timedelta(hours=4)).status_code == 200
    pending = items(reviewer, tenant, 'PENDING_VERIFICATION')
    assert pending['total'] == 2
    assert any(t['deposit_id'] is None for t in pending['items'])
    registry_task = next(t for t in pending['items'] if not t['deposit_id'])
    notices = reviewer.get(f"/api/v1/interventions/{registry_task['id']}/notifications").json()
    assert notices
    from sentinel.db import session_factory
    from sentinel.delivery import deliver_one
    from sentinel.models import NotificationDelivery
    with session_factory()() as db:
        delivery = db.scalar(select(NotificationDelivery.id).where(NotificationDelivery.notification_id == notices[0]['id']))
    assert deliver_one(delivery) == 'SENT'  # Institution-only notice has no deposit FK.


def test_reports_full_counts_pagination_scope_csv_and_revoked_supervisor(clients):
    from sentinel.models import now
    tenant, _, reviewer = workspace(clients)
    supervisor = clients('approver').get('/api/v1/me').json()['subject']
    assert configured(reviewer, tenant, supervisor_subject=supervisor).status_code == 200
    # Revocation before deadline must prevent supervisor delivery, including future-clock scans.
    assert post(clients('operator'), '/operator/assignments', {'subject': supervisor, 'role': 'APPROVER',
        'scope_type': 'INSTITUTION', 'scope_id': tenant, 'enabled': False,
        'reason': 'Revoke fictional supervisor scope before escalation.'}).status_code == 200
    scan(reviewer, tenant, now() + timedelta(days=4))
    first = items(reviewer, tenant, limit=1)
    assert first['total'] >= 2 and len(first['items']) == 1 and first['next_cursor']
    second = items(reviewer, tenant, after=first['next_cursor'], limit=1)
    assert second['items'][0]['id'] != first['items'][0]['id'] and second['total'] == first['total']
    for task in items(reviewer, tenant)['items']:
        assert not any(n['kind'] == 'OPERATIONS_ESCALATION' for n in reviewer.get(
            f"/api/v1/interventions/{task['id']}/notifications").json())
        assert clients('other-institution').get(f"/api/v1/interventions/{task['id']}/notifications").status_code == 404
    assert items(clients('other-institution'), tenant)['total'] == 0
    assert scan(clients(), tenant).status_code == 403
    report = reviewer.get('/api/v1/reports/interventions.csv', params={'institution_id': tenant})
    assert report.status_code == 200 and 'SYNTHETIC_PRODUCT_SLA' in report.text and 'MISSING_DOCUMENTS' in report.text
    assert tenant not in clients('other-institution').get('/api/v1/reports/interventions.csv').text


def test_concurrent_scans_one_episode_and_one_notification_per_recipient(clients):
    from sentinel.db import session_factory
    from sentinel.models import Intervention, Notification, now
    from sentinel.operations import scan as service_scan
    tenant, _, _ = workspace(clients)
    def execute(_):
        with session_factory()() as db:
            result = service_scan(db, [tenant], now() + timedelta(days=4))
            db.commit()
            return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, range(2)))
    assert sum(r['created'] for r in results) == 2
    with session_factory()() as db:
        assert db.scalar(select(func.count()).select_from(Intervention).where(Intervention.institution_id == tenant)) == 2
        notifications = db.scalars(select(Notification).where(Notification.institution_id == tenant)).all()
        assert len(notifications) == len({n.dedupe_key for n in notifications}) == 4


def test_queued_operational_mail_cancelled_after_scope_revocation(clients):
    from sentinel.db import session_factory
    from sentinel.delivery import deliver_one
    from sentinel.models import NotificationDelivery, now
    tenant, _, reviewer = workspace(clients)
    supervisor = clients('approver').get('/api/v1/me').json()['subject']
    assert configured(reviewer, tenant, supervisor_subject=supervisor).status_code == 200
    scan(reviewer, tenant, now() + timedelta(days=4))
    task = items(reviewer, tenant, 'MISSING_DOCUMENTS')['items'][0]
    notices = reviewer.get(f"/api/v1/interventions/{task['id']}/notifications").json()
    notice = next(n for n in notices if n['kind'] == 'OPERATIONS_ESCALATION')
    assert post(clients('operator'), '/operator/assignments', {'subject': supervisor, 'role': 'APPROVER',
        'scope_type': 'INSTITUTION', 'scope_id': tenant, 'enabled': False,
        'reason': 'Revoke fictional supervisor before queued SMTP delivery.'}).status_code == 200
    with session_factory()() as db:
        delivery = db.scalar(select(NotificationDelivery.id).where(NotificationDelivery.notification_id == notice['id']))
    assert deliver_one(delivery) == 'CANCELLED'


def test_bureau_holds_case_evidence_and_custom_maturity_bands(clients):
    from sentinel.db import session_factory
    from sentinel.lifecycle import run_maturity
    from sentinel.models import now
    from test_lifecycle import accepted, clear, prepared_case
    # Existing actual-service helper supplies a fully scrutinized/accepted instrument.
    deposit = accepted(clients)
    reviewer = clients('reviewer')
    case = post(clients(), '/release-cases', {'deposit_id': deposit['id'], 'reason': 'TERM_COMPLETED'})
    assert case.status_code == 200, case.text
    tenant = deposit['institution_id']
    scan(reviewer, tenant, now() + timedelta(days=4))
    assert any(t['case_id'] == case.json()['id'] for t in items(reviewer, tenant, 'MISSING_DOCUMENTS', deposit_id=deposit['id'])['items'])
    prepared_deposit, prepared = prepared_case(clients)
    held = post(reviewer, f"/release-cases/{prepared['id']}/holds", {
        'expected_version': prepared['version'], 'kind': 'MANUAL',
        'reason': 'Fictional unresolved hold for operational follow-up.'})
    assert held.status_code == 200, held.text
    scan(reviewer, tenant, now() + timedelta(days=4))
    clearances = [t for t in items(reviewer, tenant, 'BUREAU_CLEARANCE', deposit_id=prepared_deposit['id'])['items']
                  if t['case_id'] == prepared['id']]
    assert len(clearances) == 3
    assert any(t['case_id'] == prepared['id'] for t in items(reviewer, tenant, 'ACTIVE_HOLD', deposit_id=prepared_deposit['id'])['items'])
    clear(clients, prepared, 'PGRC', 'pgrc')
    scan(reviewer, tenant)
    assert not any(t['case_id'] == prepared['id'] and t['detail']['bureau'] == 'PGRC'
                   for t in items(reviewer, tenant, 'BUREAU_CLEARANCE', deposit_id=prepared_deposit['id'])['items'])
    # Separate policy instance avoids changing the shared seeded institution's reminders.
    tenant, deposit, reviewer = workspace(clients)
    assert configured(reviewer, tenant, maturity_days=[60, 14]).status_code == 200
    from datetime import date
    with session_factory()() as db:
        response = run_maturity(db, date(2026, 9, 20), [tenant])
        db.commit()
        assert response['notifications_created'] == 1
    notifications = reviewer.get('/api/v1/notifications', params={'deposit_id': deposit['id'], 'kind': 'MATURITY_IN_APP'}).json()
    assert notifications[0]['detail']['threshold'] == 14
