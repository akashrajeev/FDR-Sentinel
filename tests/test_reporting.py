import pytest
from conftest import create_deposit, latest, post
from test_lifecycle import prepared_case

pytestmark = pytest.mark.integration


def test_summary_search_export_scope(clients):
    maker, other = clients(), clients('other-institution')
    record = create_deposit(maker)
    result = maker.get('/api/v1/dashboard/summary')
    assert result.status_code == 200
    assert int(result.json()['declared_total_paise']) >= record['amount_paise']
    assert result.json()['actual_financial_releases'] == 0
    found = maker.get('/api/v1/search/deposits', params={'q': record['id'][:12]}).json()
    assert [r['id'] for r in found] == [record['id']]
    assert other.get('/api/v1/search/deposits', params={'q': record['id']}).json() == []
    assert maker.get('/api/v1/search/deposits', params={'q': '%_'}).json() == []
    csv = maker.get('/api/v1/reports/deposits.csv')
    assert csv.status_code == 200 and record['id'] in csv.text
    assert 'reference_digest' not in csv.text
    assert record['id'] not in other.get('/api/v1/reports/deposits.csv').text
    page = maker.get('/api/v1/search/deposits', params={'limit': 2}).json()
    next_page = maker.get('/api/v1/search/deposits', params={'limit': 2, 'after': page[-1]['id']}).json()
    assert not {r['id'] for r in page} & {r['id'] for r in next_page}


def test_csv_injection_escaping():
    from sentinel.reporting_api import csv_safe
    for text in ('=SUM(1,2)', '+cmd', '-cmd', '@cmd', '\ufeff=cmd', ' \t=cmd'):
        assert csv_safe(text).startswith("'")


def test_revalidation_invalidates_pending_release_and_keeps_history(clients):
    deposit, case = prepared_case(clients)
    response = post(clients(), f"/deposits/{deposit['id']}/request-revalidation", {
        'expected_version': latest(clients(), deposit)['version']})
    assert response.status_code == 200
    assert response.json()['workflow'] == 'PENDING_SCRUTINY'
    assert clients().get('/api/v1/release-cases/' + case['id']).json()['state'] == 'DRAFT'
    assert latest(clients(), deposit)['decisions']


def test_policy_and_obligation_scope_are_explicit(clients):
    result = clients().get('/api/v1/policies/current').json()
    assert result['production_activation'].startswith('BLOCKED')
    assert result['policy']['legal_effective_from'] is None
    response = post(clients(), '/obligations', {'institution_id': '20000000-0000-0000-0000-000000000001',
        'regulatory_event': 'NEW_INSTITUTION', 'coverage_mode': 'AGGREGATE_REVIEW'})
    assert response.status_code == 200
    assert response.json()['coverage_mode'] == 'AGGREGATE_REVIEW'
