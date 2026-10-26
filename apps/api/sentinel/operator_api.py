from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from sentinel.auth import Actor, authenticate
from sentinel.db import get_db
from sentinel.models import Institution, Principal, RoleBinding
from sentinel.schemas import StrictModel
from sentinel.transactions import mutate

router = APIRouter(prefix='/api/v1/operator')


def technical_operator(actor: Actor = Depends(authenticate)):
    if not actor.allows('OPERATOR', 'BUREAU', 'PLATFORM'):
        raise HTTPException(403, 'Technical operator scope required')
    return actor


class Assignment(StrictModel):
    subject: str = Field(min_length=1, max_length=128)
    role: Literal['REVIEWER', 'AUDITOR', 'CLEARANCE', 'APPROVER', 'ISSUER']
    scope_type: Literal['INSTITUTION', 'BUREAU', 'CASE']
    scope_id: str = Field(min_length=1, max_length=64)
    enabled: bool = True
    valid_until: datetime | None = None
    reason: str = Field(min_length=10, max_length=2000)


@router.get('/workspace')
def workspace(actor: Actor = Depends(technical_operator), db: Session = Depends(get_db)):
    institutions = [{'id': i.id, 'external_id': i.external_id, 'legal_name': i.legal_name}
                    for i in db.scalars(select(Institution).order_by(Institution.created_at.desc()).limit(2000))]
    names = ['institution', 'other-institution', 'reviewer', 'pgrc', 'vigilance', 'approver', 'issuer', 'auditor']
    aliases = {f'10000000-0000-0000-0000-{index:012d}': name for index, name in enumerate(names, 1)}
    principals = [{'subject': p.subject, 'enabled': p.enabled,
                   'label': aliases.get(p.subject, 'operator' if p.subject == actor.subject else p.subject)}
                  for p in db.scalars(select(Principal).order_by(Principal.subject).limit(2000))]
    bindings = [{'id': b.id, 'subject': b.subject, 'role': b.role, 'scope_type': b.scope_type,
                 'scope_id': b.scope_id, 'enabled': b.enabled,
                 'valid_until': b.valid_until.isoformat() if b.valid_until else None}
                for b in db.scalars(select(RoleBinding).order_by(RoleBinding.valid_from.desc()).limit(500))]
    return {'institutions': institutions, 'principals': principals, 'bindings': bindings,
            'note': 'Technical scope administration only; no financial decision or document authority'}


@router.post('/assignments')
def assign(body: Assignment, request: Request, actor: Actor = Depends(technical_operator),
           db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    if body.subject == actor.subject:
        raise HTTPException(403, 'Operator self-grants prohibited')
    expiry = body.valid_until or datetime.now(timezone.utc) + timedelta(days=30)
    if not expiry.tzinfo or not datetime.now(timezone.utc) < expiry <= datetime.now(timezone.utc) + timedelta(days=90):
        raise HTTPException(422, 'Validity must be timezone-aware, future and at most 90 days')
    def action():
        try:
            binding = db.scalar(text('SELECT public.operator_assign_scope(:actor,:target,:role,:scope_type,:scope_id,'
                ':enabled,:until,:reason,:request)'), {'actor': actor.subject, 'target': body.subject, 'role': body.role,
                'scope_type': body.scope_type, 'scope_id': body.scope_id, 'enabled': body.enabled, 'until': expiry,
                'reason': body.reason, 'request': request.state.request_id})
        except DBAPIError:
            raise HTTPException(409, 'Assignment rejected: check active principal, scope and bureau/role compatibility') from None
        return {'id': binding, 'enabled': body.enabled, 'valid_until': expiry.isoformat()}
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)
