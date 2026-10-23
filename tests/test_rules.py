import copy

import pytest
from sentinel.compliance import POLICY_REVISION, digest, required_amount

CONTEXT = {'academic_year': '2026-27', 'governance': 'PRIVATE', 'programme': 'ENGINEERING_UG',
           'land': 'OWNED', 'exceptional_context': False}


@pytest.mark.parametrize(('changes', 'event', 'expected'), [
    ({}, 'NEW_INSTITUTION', 350000000),
    ({'land': 'PRIVATE_LEASE'}, 'NEW_INSTITUTION', 700000000),
    ({'governance': 'GOVERNMENT'}, 'NEW_INSTITUTION', 0),
    ({'governance': 'GOVERNMENT_AIDED'}, 'NEW_INSTITUTION', 0),
    ({'academic_year': '2027-28'}, 'NEW_INSTITUTION', None),
    ({'exceptional_context': True}, 'NEW_INSTITUTION', None),
    ({'programme': 'OTHER'}, 'NEW_INSTITUTION', None),
    ({'land': 'UNKNOWN'}, 'NEW_INSTITUTION', None),
    ({}, 'HISTORICAL_RECORD', None),
])
def test_scoped_policy(changes, event, expected):
    context = copy.deepcopy(CONTEXT)
    context.update(changes)
    assert required_amount(context, event) == expected


def test_reproducible_policy_digest():
    assert len(POLICY_REVISION) == 64
    assert digest({'a': 1, 'b': 2}) == digest({'b': 2, 'a': 1})


@pytest.mark.parametrize(('programme', 'level', 'expected'), [
    ('ENGINEERING', 'DIPLOMA', 150000000), ('ENGINEERING', 'PG', 150000000),
    ('PLANNING', 'UG', 150000000), ('APPLIED_ARTS', 'DIPLOMA', 150000000),
    ('DESIGN', 'PG', 150000000), ('HMCT', 'UG', 150000000),
    ('COMPUTER_APPLICATIONS', 'UG', 50000000), ('MANAGEMENT', 'UG', 50000000),
    ('MANAGEMENT', 'PG', 150000000), ('COMPUTER_APPLICATIONS', 'DIPLOMA', None),
])
def test_table_programme_scope(programme, level, expected):
    context = {**CONTEXT, 'programme': programme, 'level': level}
    assert required_amount(context, 'NEW_INSTITUTION') == expected
