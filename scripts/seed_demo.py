"""Idempotent synthetic identity and institution bootstrap; no financial records."""
from sentinel.compliance import POLICY_REVISION
from sentinel.db import session_factory
from sentinel.models import Institution, Obligation, Principal, RoleBinding
from sqlalchemy import select

INSTITUTION_ID = '20000000-0000-0000-0000-000000000001'
OBLIGATION_ID = '30000000-0000-0000-0000-000000000001'
CONTEXT = {'academic_year': '2026-27', 'governance': 'PRIVATE', 'programme': 'ENGINEERING_UG',
           'land': 'OWNED', 'exceptional_context': False}


def seed(db):
    subjects = [f'10000000-0000-0000-0000-{i:012d}' for i in range(1, 9)]
    for subject in subjects:
        if not db.get(Principal, subject):
            db.add(Principal(subject=subject))
    db.flush()
    if not db.get(Institution, INSTITUTION_ID):
        db.add(Institution(id=INSTITUTION_ID, external_id='SYNTHETIC-001',
                           legal_name='Sentinel Institute of Technology (Synthetic)',
                           context=CONTEXT, owner=subjects[0]))
        db.flush()
        db.add(Obligation(id=OBLIGATION_ID, institution_id=INSTITUTION_ID, regulatory_event='NEW_INSTITUTION',
                          context=CONTEXT, required_amount_paise=350000000, policy_revision=POLICY_REVISION))
    bindings = [(0, 'MAKER', 'INSTITUTION', INSTITUTION_ID),
                (2, 'REVIEWER', 'INSTITUTION', INSTITUTION_ID),
                (2, 'CLEARANCE', 'BUREAU', 'GRANTS'),
                (3, 'AUDITOR', 'INSTITUTION', INSTITUTION_ID),
                (3, 'CLEARANCE', 'BUREAU', 'PGRC'),
                (4, 'AUDITOR', 'INSTITUTION', INSTITUTION_ID),
                (4, 'CLEARANCE', 'BUREAU', 'VIGILANCE'),
                (5, 'APPROVER', 'INSTITUTION', INSTITUTION_ID),
                (6, 'ISSUER', 'INSTITUTION', INSTITUTION_ID),
                (6, 'ISSUER', 'BUREAU', 'APPROVAL_BUREAU'),
                (6, 'ISSUER', 'BUREAU', 'COUNCIL'),
                (7, 'AUDITOR', 'INSTITUTION', INSTITUTION_ID)]
    for index, role, scope_type, scope_id in bindings:
        if not db.scalar(select(RoleBinding.id).where(RoleBinding.subject == subjects[index],
                         RoleBinding.role == role, RoleBinding.scope_type == scope_type,
                         RoleBinding.scope_id == scope_id)):
            db.add(RoleBinding(subject=subjects[index], role=role, scope_type=scope_type, scope_id=scope_id))
    db.commit()


if __name__ == '__main__':
    with session_factory()() as db:
        seed(db)
    print('Synthetic institution and explicit role scopes provisioned; bank/AICTE NOT_CONNECTED.')
