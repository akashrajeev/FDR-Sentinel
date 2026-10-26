from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from sentinel import integrations, lifecycle
from sentinel.auth import Actor, authenticate, require_scope
from sentinel.db import get_db
from sentinel.models import Deposit, Institution, IntegrationRequest
from sentinel.schemas import StrictModel, VersionCommand
from sentinel.services import check_version, get_deposit
from sentinel.transactions import audit, mutate

router = APIRouter(prefix='/api/v1')


class SandboxCommand(StrictModel):
    expected_version: int = Field(strict=True, ge=1)
    ledger_id: str | None = Field(default=None, pattern=r'^SB-[A-Za-z0-9-]{3,55}$')
    behavior: Literal['NORMAL', 'DELAYED', 'TRANSIENT_FAILURE'] = 'NORMAL'


class RegistryCommand(StrictModel):
    behavior: Literal['NORMAL', 'DELAYED', 'TRANSIENT_FAILURE'] = 'NORMAL'


@router.get('/sandbox/catalogue')
def catalogue(actor: Actor = Depends(authenticate)):
    try:
        return integrations.call_sandbox('GET', '/v1/catalogue')
    except Exception:
        raise HTTPException(503, 'Independent sandbox unavailable') from None


@router.get('/integration-requests')
def listing(deposit_id: str | None = None, institution_id: str | None = None, case_id: str | None = None,
            actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    query = select(IntegrationRequest).where(or_(IntegrationRequest.institution_id.in_(actor.institution_ids()),
                                                IntegrationRequest.case_id.in_(actor.case_ids())))
    if deposit_id:
        query = query.where(IntegrationRequest.deposit_id == deposit_id)
    if institution_id:
        query = query.where(IntegrationRequest.institution_id == institution_id)
    if case_id:
        query = query.where(IntegrationRequest.case_id == case_id)
    return [integrations.dto(r) for r in db.scalars(query.order_by(IntegrationRequest.created_at.desc()).limit(100))]


@router.post('/institutions/{institution_id}/registry-check')
def registry(institution_id: str, body: RegistryCommand, request: Request,
             actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
             idempotency_key: str | None = Header(None)):
    require_scope(actor, institution_id, ['MAKER', 'REVIEWER'])
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(404, 'Institution not found')
    return mutate(db, actor, request, idempotency_key, body.model_dump(),
        lambda: integrations.enqueue(db, actor, institution, 'REGISTRY_LOOKUP', body.behavior))


@router.post('/deposits/{deposit_id}/bank-check')
def bank(deposit_id: str, body: SandboxCommand, request: Request, actor: Actor = Depends(authenticate),
         db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    get_deposit(db, actor, deposit_id, roles=['REVIEWER'])
    if not body.ledger_id:
        raise HTTPException(422, 'Independent sandbox ledger ID required')
    def action():
        deposit = get_deposit(db, actor, deposit_id, lock=True, roles=['REVIEWER'])
        check_version(deposit, body.expected_version)
        deposit.version += 1
        return integrations.enqueue(db, actor, db.get(Institution, deposit.institution_id), 'BANK_VERIFY',
                                    body.behavior, deposit=deposit, ledger_id=body.ledger_id)
    return mutate(db, actor, request, idempotency_key, body.model_dump(), action)


@router.post('/release-cases/{case_id}/sandbox-exchange')
def case_exchange(case_id: str, body: SandboxCommand, request: Request, actor: Actor = Depends(authenticate),
                  db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id, roles=['ISSUER'])
    def action():
        case = lifecycle.get_case(db, actor, case_id, lock=True, roles=['ISSUER'])
        lifecycle.case_version(case, body.expected_version, ['ISSUED_SYNTHETIC'])
        if actor.subject != case.issuer:
            raise HTTPException(403, 'Only the recorded human issuer may request reconciliation')
        lifecycle.gate_approval(db, case)
        existing = db.scalar(select(IntegrationRequest).where(
            IntegrationRequest.case_id == case.id, IntegrationRequest.operation == ('RELEASE_ACK' if body.ledger_id else 'CASE_SYNC')))
        if existing:
            if existing.payload.get('ledger_id') != body.ledger_id:
                raise HTTPException(409, 'A different reconciliation target already exists')
            return integrations.dto(existing)
        deposit = db.get(Deposit, case.deposit_id)
        return integrations.enqueue(db, actor, db.get(Institution, case.institution_id),
            'RELEASE_ACK' if body.ledger_id else 'CASE_SYNC', body.behavior, deposit=deposit,
            case=case, ledger_id=body.ledger_id)
    return mutate(db, actor, request, idempotency_key, body.model_dump(), action)


@router.post('/integration-requests/{integration_id}/retry')
def retry(integration_id: str, body: VersionCommand, request: Request, actor: Actor = Depends(authenticate),
          db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    row = db.get(IntegrationRequest, integration_id)
    if not row:
        raise HTTPException(404, 'Request not found')
    require_scope(actor, row.institution_id, ['REVIEWER', 'ISSUER'])
    def action():
        from sentinel.models import now
        row = db.scalar(select(IntegrationRequest).where(IntegrationRequest.id == integration_id).with_for_update()
                        .execution_options(populate_existing=True))
        if row.state != 'DEAD_LETTER' or row.attempts != body.expected_version:
            raise HTTPException(409, 'Stale or non-dead-letter request')
        row.state, row.attempts, row.next_attempt_at = 'WAITING', 0, now()
        audit(db, row.institution_id, actor.subject, 'SANDBOX_REQUEST_RETRIED', row.id, {}, request.state.request_id)
        return integrations.dto(row)
    return mutate(db, actor, request, idempotency_key, body.model_dump(), action)
