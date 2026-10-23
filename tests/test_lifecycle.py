from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pymupdf
import pytest
from conftest import create_deposit, evaluate_submit, latest, pdf_bytes, post
from sqlalchemy import select

pytestmark = pytest.mark.integration


def accepted(clients, kind='FDR', issue='2016-10-01', maturity='2026-10-01'):
    maker = clients()
    deposit = create_deposit(maker, kind=kind)
    if kind in ('RTGS', 'ONLINE'):
        corrected = post(maker, f"/deposits/{deposit['id']}/correct", {
            'expected_version': deposit['version'], 'amount_paise': 350000000, 'deposited_on': '2016-10-01'})
        assert corrected.status_code == 200
    if kind == 'FDR' and issue != '2016-10-01':
        correction = post(maker, f"/deposits/{deposit['id']}/correct", {
            'expected_version': deposit['version'], 'amount_paise': 350000000,
            'issue_date': issue, 'maturity_date': maturity})
        assert correction.status_code == 200
    data = pdf_bytes(issue=issue, maturity=maturity) if kind == 'FDR' else pdf_bytes()
    document = maker.post(f"/api/v1/deposits/{deposit['id']}/documents", files={
        'file': ('proof.pdf', data, 'application/pdf')}, headers={'Idempotency-Key': str(uuid4())})
    assert document.status_code == 200
    process(document.json()['id'])
    current = evaluate_submit(maker, deposit)
    result = post(clients('reviewer'), f"/deposits/{deposit['id']}/review", {
        'expected_version': current['version'], 'decision': 'ACCEPT_REGISTRATION',
        'reason': 'Synthetic evidence reviewed; no bank authentication claimed.', 'evidence_reviewed': True})
    assert result.status_code == 200, result.text
    return result.json()


def process(document_id):
    from sentinel.db import session_factory
    from sentinel.jobs import process_document
    from sentinel.models import Outbox
    with session_factory()() as db:
        event_id = db.scalar(select(Outbox.id).where(Outbox.aggregate_id == document_id))
    assert process_document.run(event_id) == 'READY'


def case_get(client, case):
    response = client.get('/api/v1/release-cases/' + case['id'])
    assert response.status_code == 200, response.text
    return response.json()


def prepared_case(clients, kind='FDR', reason='TERM_COMPLETED', submit=True):
    maker = clients()
    deposit = accepted(clients, kind=kind)
    result = post(maker, '/release-cases', {'deposit_id': deposit['id'], 'reason': reason})
    assert result.status_code == 200, result.text
    case = result.json()
    categories = ['REQUEST_LETTER', 'AFFIDAVIT_6', 'APPROVAL_LETTER']
    if reason != 'TERM_COMPLETED':
        categories.append({'CLOSURE': 'CLOSURE_ORDER', 'MERGER': 'MERGER_ORDER',
                           'CONVERSION': 'CONVERSION_ORDER', 'OTHER': 'SUPPORTING'}[reason])
    for category in categories:
        result = maker.post(f"/api/v1/release-cases/{case['id']}/documents", data={'category': category},
                            files={'file': ('synthetic.pdf', pdf_bytes(), 'application/pdf')},
                            headers={'Idempotency-Key': str(uuid4())})
        assert result.status_code == 200, result.text
        process(result.json()['id'])
    case = case_get(maker, case)
    if submit:
        result = post(maker, f"/release-cases/{case['id']}/submit", {'expected_version': case['version']})
        assert result.status_code == 200, result.text
        case = result.json()
    return deposit, case


def clear(clients, case, bureau, user):
    current = case_get(clients(), case)
    response = post(clients(user), f"/release-cases/{case['id']}/clearances/{bureau}/decision", {
        'expected_version': current['version'], 'decision': 'CLEARED',
        'reason': 'Synthetic bureau evidence examined and clearance recorded.',
        'evidence_document_id': current['documents'][0]['id']})
    assert response.status_code == 200, response.text
    return response.json()


def approve_body(case):
    return {'expected_version': case['version'], 'synthetic_acknowledgement': True,
            'regulatory_basis': 'Synthetic term and applicability review; APH 6.46 remains provisional; no legal authority.'}


def test_e4_pgrc_block_independent_approval_and_synthetic_noc(clients):
    deposit, case = prepared_case(clients)
    case = clear(clients, case, 'VIGILANCE', 'vigilance')
    case = clear(clients, case, 'GRANTS', 'reviewer')
    blocked = post(clients('approver'), f"/release-cases/{case['id']}/approve", approve_body(case))
    assert blocked.status_code == 409 and 'PGRC' in blocked.text
    wrong_bureau = post(clients('pgrc'), f"/release-cases/{case['id']}/clearances/VIGILANCE/decision", {
        'expected_version': case['version'], 'decision': 'CLEARED', 'reason': 'Invalid cross-bureau attempt',
        'evidence_document_id': case['documents'][0]['id']})
    assert wrong_bureau.status_code == 403
    assert post(clients(), f"/release-cases/{case['id']}/approve", approve_body(case)).status_code == 403
    case = clear(clients, case, 'PGRC', 'pgrc')
    assert case['state'] == 'APPROVAL_REVIEW'
    result = post(clients('approver'), f"/release-cases/{case['id']}/approve", approve_body(case))
    assert result.status_code == 200, result.text
    case = result.json()
    key = str(uuid4())
    result = post(clients('issuer'), f"/release-cases/{case['id']}/issue-document", {
        'expected_version': case['version']}, key)
    assert result.status_code == 200, result.text
    issued = result.json()
    replay = post(clients('issuer'), f"/release-cases/{case['id']}/issue-document", {
        'expected_version': case['version']}, key)
    assert replay.json() == issued
    assert issued['state'] == 'ISSUED_SYNTHETIC'
    response = clients().get(f"/api/v1/documents/{issued['output_document_id']}/content")
    assert response.status_code == 200
    with pymupdf.open(stream=response.content, filetype='pdf') as pdf:
        text = pdf[0].get_text()
    assert 'SYNTHETIC' in text and 'Sample NOC' in text and 'NO PAYMENT' in text
    assert latest(clients(), deposit)['lifecycle_status'] != 'RELEASED'


def test_rtgs_sanction_branch_without_maturity(clients):
    _, case = prepared_case(clients, kind='RTGS')
    for bureau, user in [('PGRC', 'pgrc'), ('VIGILANCE', 'vigilance'), ('GRANTS', 'reviewer')]:
        case = clear(clients, case, bureau, user)
    result = post(clients('approver'), f"/release-cases/{case['id']}/approve", approve_body(case))
    assert result.status_code == 200
    case = result.json()
    result = post(clients('issuer'), f"/release-cases/{case['id']}/issue-document", {'expected_version': case['version']})
    assert result.status_code == 200
    content = clients().get(f"/api/v1/documents/{result.json()['output_document_id']}/content").content
    with pymupdf.open(stream=content, filetype='pdf') as pdf:
        assert 'SANCTION ORDER' in pdf[0].get_text()


@pytest.mark.parametrize('reason', ['CLOSURE', 'MERGER', 'CONVERSION', 'OTHER'])
def test_e5_exception_evidence_and_hold(clients, reason):
    _, case = prepared_case(clients, reason=reason)
    assert any(h['active'] and reason in h['reason'] for h in case['holds'])
    for bureau, user in [('PGRC', 'pgrc'), ('VIGILANCE', 'vigilance'), ('GRANTS', 'reviewer')]:
        case = clear(clients, case, bureau, user)
    assert post(clients('approver'), f"/release-cases/{case['id']}/approve", approve_body(case)).status_code == 409
    hold = case['holds'][0]
    resolved = post(clients('approver'), f"/release-cases/{case['id']}/holds/{hold['id']}/resolve", {
        'expected_version': case['version'], 'resolution': 'Synthetic branch evidence and authorized policy basis reviewed.',
        'evidence_document_id': next(d['id'] for d in case['documents'] if d['category'].endswith('ORDER')
                                     or d['category'] == 'SUPPORTING')})
    assert resolved.status_code == 200, resolved.text
    assert not resolved.json()['holds'][0]['active']


def test_e6_two_officers_cannot_complete_same_version(clients):
    _, case = prepared_case(clients)
    body = {'expected_version': case['version'], 'decision': 'CLEARED', 'reason': 'Concurrent synthetic decision',
            'evidence_document_id': case['documents'][0]['id']}
    def action(index):
        user, bureau = [('pgrc', 'PGRC'), ('vigilance', 'VIGILANCE')][index]
        return post(clients(user), f"/release-cases/{case['id']}/clearances/{bureau}/decision", body).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(action, range(2)))
    assert sorted(result) == [200, 409]


def test_clearance_rejection_and_return_invalidates_prior_clearances(clients):
    _, case = prepared_case(clients)
    rejected = post(clients('pgrc'), f"/release-cases/{case['id']}/clearances/PGRC/decision", {
        'expected_version': case['version'], 'decision': 'REJECTED',
        'reason': 'Synthetic pending grievance requires additional evidence.',
        'evidence_document_id': case['documents'][0]['id']})
    assert rejected.status_code == 200
    assert rejected.json()['holds'][0]['active']
    returned = post(clients('reviewer'), f"/release-cases/{case['id']}/return", {
        'expected_version': rejected.json()['version'], 'reason': 'Return for additional grievance resolution evidence.'})
    assert returned.status_code == 200
    assert returned.json()['state'] == 'DRAFT' and returned.json()['clearances'] == []
    assert returned.json()['holds'][0]['active']


def test_maturity_alerts_idempotent_never_release(clients):
    deposit = create_deposit(clients())
    first = post(clients('reviewer'), '/monitoring/run', {'as_of': '2026-09-24'})
    assert first.status_code == 200
    from sentinel.db import session_factory
    from sentinel.models import Notification
    with session_factory()() as db:
        count = len(db.scalars(select(Notification).where(Notification.deposit_id == deposit['id'])).all())
    assert count == 1
    assert post(clients('reviewer'), '/monitoring/run', {'as_of': '2026-09-24'}).status_code == 200
    with session_factory()() as db:
        assert len(db.scalars(select(Notification).where(Notification.deposit_id == deposit['id'])).all()) == count
    assert latest(clients(), deposit)['lifecycle_status'] == 'APPROACHING_MATURITY'
    assert latest(clients(), deposit)['workflow'] == 'DRAFT'


def test_case_scoped_identity_does_not_gain_institution_access(clients):
    from sentinel.db import session_factory
    from sentinel.models import RoleBinding
    _, case = prepared_case(clients)
    with session_factory()() as db:
        binding = RoleBinding(subject='10000000-0000-0000-0000-000000000002', role='AUDITOR',
                              scope_type='CASE', scope_id=case['id'])
        db.add(binding)
        db.commit()
        binding_id = binding.id
    try:
        outsider = clients('other-institution')
        response = outsider.get('/api/v1/release-cases/' + case['id'])
        assert response.status_code == 200
        assert outsider.get('/api/v1/institutions/' + case['institution_id']).status_code == 404
        assert outsider.get('/api/v1/documents/' + case['documents'][0]['id'] + '/content').status_code == 200
        assert post(outsider, f"/release-cases/{case['id']}/submit", {'expected_version': case['version']}).status_code == 404
    finally:
        with session_factory()() as db:
            db.delete(db.get(RoleBinding, binding_id))
            db.commit()


def test_final_approver_cannot_be_prior_clearance_actor_after_role_change(clients):
    from sentinel.db import session_factory
    from sentinel.models import RoleBinding
    _, case = prepared_case(clients)
    for bureau, user in [('PGRC', 'pgrc'), ('VIGILANCE', 'vigilance'), ('GRANTS', 'reviewer')]:
        case = clear(clients, case, bureau, user)
    with session_factory()() as db:
        binding = RoleBinding(subject='10000000-0000-0000-0000-000000000004', role='APPROVER',
                              scope_type='INSTITUTION', scope_id=case['institution_id'])
        db.add(binding)
        db.commit()
        binding_id = binding.id
    try:
        result = post(clients('pgrc'), f"/release-cases/{case['id']}/approve", approve_body(case))
        assert result.status_code == 403
    finally:
        with session_factory()() as db:
            db.delete(db.get(RoleBinding, binding_id))
            db.commit()


def test_replacement_authorized_lineage_retains_original(clients):
    old = accepted(clients)
    new = accepted(clients, issue='2026-10-02', maturity='2027-10-02')
    evidence = latest(clients(), new)['documents'][0]['id']
    request = post(clients(), '/replacements', {'old_deposit_id': old['id'], 'new_deposit_id': new['id'],
        'expected_old_version': old['version'], 'kind': 'RENEWAL',
        'rationale': 'Synthetic renewal recorded with explicit policy review.', 'evidence_document_id': evidence})
    assert request.status_code == 200, request.text
    record = request.json()
    response = post(clients('reviewer'), f"/replacements/{record['id']}/approve", {
        'expected_version': record['version'], 'policy_basis': 'Synthetic legacy renewal exception reviewed; not blanket renewal permission.'})
    assert response.status_code == 200, response.text
    assert latest(clients(), old)['lifecycle_status'] == 'REPLACED'
    assert latest(clients(), old)['documents']
    assert latest(clients(), new)['verification_status'] == 'MANUALLY_REVIEWED'


def test_financial_hold_requires_external_body_noc(clients):
    _, case = prepared_case(clients)
    result = post(clients('reviewer'), f"/release-cases/{case['id']}/holds", {
        'expected_version': case['version'], 'kind': 'FINANCIAL_EMBEZZLEMENT',
        'reason': 'Synthetic Government body financial hold; corresponding body NOC required.'})
    assert result.status_code == 200
    case = result.json()
    hold = case['holds'][0]
    assert hold['required_category'] == 'EXTERNAL_BODY_NOC'
    wrong = post(clients('approver'), f"/release-cases/{case['id']}/holds/{hold['id']}/resolve", {
        'expected_version': case['version'], 'resolution': 'Wrong category must not satisfy a financial hold.',
        'evidence_document_id': case['documents'][0]['id']})
    assert wrong.status_code == 409
