"""Operator-only scoped provisioning; no financial decision authority in this command."""
import argparse
from datetime import datetime, timezone

from sentinel.db import session_factory
from sentinel.models import Institution, Principal, ReleaseCase, RoleBinding
from sentinel.transactions import audit
from sqlalchemy import select

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--subject', required=True, help='Exact OIDC sub, not a display name')
parser.add_argument('--role', required=True, choices=['MAKER', 'REVIEWER', 'AUDITOR', 'CLEARANCE', 'APPROVER', 'ISSUER'])
parser.add_argument('--scope-type', required=True, choices=['INSTITUTION', 'BUREAU', 'CASE'])
parser.add_argument('--scope-id', required=True)
parser.add_argument('--reason', required=True)
parser.add_argument('--valid-until', help='ISO UTC timestamp; no perpetual scope if temporary assignment is intended')
parser.add_argument('--disable', action='store_true')
args = parser.parse_args()
if len(args.reason.strip()) < 10:
    parser.error('A specific reason of at least 10 characters is required')
valid_until = datetime.fromisoformat(args.valid_until) if args.valid_until else None
if valid_until and (not valid_until.tzinfo or valid_until <= datetime.now(timezone.utc)):
    parser.error('valid-until must be a future timestamp with timezone')
with session_factory()() as db:
    principal = db.get(Principal, args.subject)
    if not principal:
        parser.error('Principal must first authenticate or be provisioned through the approved IdP')
    institution_id = None
    if args.scope_type == 'INSTITUTION':
        record = db.get(Institution, args.scope_id)
        if not record:
            parser.error('Institution does not exist')
        institution_id = record.id
    elif args.scope_type == 'CASE':
        record = db.get(ReleaseCase, args.scope_id)
        if not record:
            parser.error('Case does not exist')
        institution_id = record.institution_id
    elif args.scope_id not in ('PGRC', 'VIGILANCE', 'GRANTS', 'APPROVAL_BUREAU', 'COUNCIL'):
        parser.error('Unrecognized bureau; define its policy and scope before provisioning')
    binding = db.scalar(select(RoleBinding).where(RoleBinding.subject == args.subject,
        RoleBinding.role == args.role, RoleBinding.scope_type == args.scope_type, RoleBinding.scope_id == args.scope_id))
    if not binding:
        binding = RoleBinding(subject=args.subject, role=args.role, scope_type=args.scope_type, scope_id=args.scope_id)
        db.add(binding)
    binding.enabled = not args.disable
    binding.valid_until = valid_until
    db.flush()
    # Bureau changes affect multiple institutions; checkpoint in each existing assigned
    # scope without inventing a global institution or financial authority.
    ids = [institution_id] if institution_id else list(db.scalars(select(RoleBinding.scope_id).where(
        RoleBinding.subject == args.subject, RoleBinding.scope_type == 'INSTITUTION')))
    if not ids:
        parser.error('Assign an institution/case access scope before assigning a bureau role')
    for tenant_id in set(ids):
        audit(db, tenant_id, 'operator-cli', 'ROLE_SCOPE_CHANGED', binding.id,
              {'subject': args.subject, 'role': args.role, 'scope_type': args.scope_type,
               'scope_id': args.scope_id, 'enabled': binding.enabled, 'reason': args.reason,
               'valid_until': valid_until.isoformat() if valid_until else None}, 'operator-provisioning')
    db.commit()
print('Scoped binding changed and audited. Maker/checker restrictions still apply.')
