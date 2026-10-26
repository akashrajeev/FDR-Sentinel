import hashlib
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from sentinel import lifecycle
from sentinel.auth import Actor, authenticate
from sentinel.config import settings
from sentinel.db import get_db
from sentinel.lifecycle_schemas import (
    ApprovalIn,
    ClearanceIn,
    HoldIn,
    HoldResolution,
    ReleaseIn,
    ReleaseOut,
    ReplacementApproval,
    ReplacementIn,
)
from sentinel.models import Notification, NotificationDelivery, ReleaseCase, Replacement, now
from sentinel.schemas import DocumentOut, StrictModel, VersionCommand
from sentinel.transactions import mutate

router = APIRouter(prefix='/api/v1')


@router.post('/release-cases', response_model=ReleaseOut)
def create(body: ReleaseIn, request: Request, actor: Actor = Depends(authenticate),
           db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    from sentinel.services import get_deposit
    get_deposit(db, actor, body.deposit_id, roles=['MAKER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.create_case(db, actor, body, request.state.request_id))


@router.get('/release-cases', response_model=list[ReleaseOut])
def listing(actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    return [lifecycle.case_detail(db, c) for c in db.scalars(select(ReleaseCase).where(
        or_(ReleaseCase.institution_id.in_(actor.institution_ids()), ReleaseCase.id.in_(actor.case_ids()))
        ).order_by(ReleaseCase.created_at.desc()).limit(100))]


@router.get('/release-cases/{case_id}', response_model=ReleaseOut)
def detail(case_id: str, actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    return lifecycle.case_detail(db, lifecycle.get_case(db, actor, case_id))


@router.post('/release-cases/{case_id}/documents', response_model=DocumentOut)
def upload(case_id: str, request: Request, file: UploadFile = File(...), category: str = Form(...),
           actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
           idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id, roles=['MAKER'])
    data = file.file.read(settings().max_upload_bytes + 1)
    if len(data) > settings().max_upload_bytes:
        raise HTTPException(413, 'PDF exceeds 10 MiB limit')
    if file.content_type != 'application/pdf' or not data.startswith(b'%PDF-'):
        raise HTTPException(422, 'Only valid PDF signature accepted')
    payload = {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'category': category}
    return mutate(db, actor, request, idempotency_key, payload,
                  lambda: lifecycle.upload_case_document(db, actor, case_id, data, category, request.state.request_id))


@router.post('/release-cases/{case_id}/submit', response_model=ReleaseOut)
def submit(case_id: str, body: VersionCommand, request: Request, actor: Actor = Depends(authenticate),
           db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id, roles=['MAKER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.submit_case(db, actor, case_id, body, request.state.request_id))


@router.post('/release-cases/{case_id}/clearances/{bureau}/decision', response_model=ReleaseOut)
def clearance(case_id: str, bureau: str, body: ClearanceIn, request: Request,
              actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
              idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id)
    if not actor.allows('CLEARANCE', 'BUREAU', bureau):
        raise HTTPException(403, 'Bureau scope required')
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.decide_clearance(db, actor, case_id, bureau, body, request.state.request_id))


@router.post('/release-cases/{case_id}/holds', response_model=ReleaseOut)
def hold(case_id: str, body: HoldIn, request: Request, actor: Actor = Depends(authenticate),
         db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id, roles=['REVIEWER', 'APPROVER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.add_hold(db, actor, case_id, body, request.state.request_id))


@router.post('/release-cases/{case_id}/return', response_model=ReleaseOut)
def return_case(case_id: str, body: HoldIn, request: Request, actor: Actor = Depends(authenticate),
                db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id, roles=['REVIEWER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.return_case(db, actor, case_id, body, request.state.request_id))


@router.post('/release-cases/{case_id}/holds/{hold_id}/resolve', response_model=ReleaseOut)
def resolve(case_id: str, hold_id: str, body: HoldResolution, request: Request,
            actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
            idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id, roles=['APPROVER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.resolve_hold(db, actor, case_id, hold_id, body, request.state.request_id))


@router.post('/release-cases/{case_id}/approve', response_model=ReleaseOut)
def approve(case_id: str, body: ApprovalIn, request: Request, actor: Actor = Depends(authenticate),
            db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id, roles=['APPROVER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.approve_case(db, actor, case_id, body, request.state.request_id))


@router.post('/release-cases/{case_id}/issue-document', response_model=ReleaseOut)
def issue(case_id: str, body: VersionCommand, request: Request, actor: Actor = Depends(authenticate),
          db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    lifecycle.get_case(db, actor, case_id, roles=['ISSUER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.issue_case(db, actor, case_id, body, request.state.request_id))


@router.post('/replacements')
def replacement(body: ReplacementIn, request: Request, actor: Actor = Depends(authenticate),
                db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    from sentinel.services import get_deposit
    get_deposit(db, actor, body.old_deposit_id, roles=['MAKER'])
    get_deposit(db, actor, body.new_deposit_id, roles=['MAKER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.request_replacement(db, actor, body, request.state.request_id))


@router.get('/replacements')
def replacements(actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    return [{'id': r.id, 'old_deposit_id': r.old_deposit_id, 'new_deposit_id': r.new_deposit_id,
             'institution_id': r.institution_id, 'kind': r.kind, 'state': r.state, 'version': r.version,
             'maker': r.maker, 'checker': r.checker, 'rationale': r.rationale}
            for r in db.scalars(select(Replacement).where(
                Replacement.institution_id.in_(actor.institution_ids())).limit(100))]


@router.post('/replacements/{relationship_id}/approve')
def replacement_approve(relationship_id: str, body: ReplacementApproval, request: Request,
                        actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
                        idempotency_key: str | None = Header(None)):
    record = db.get(Replacement, relationship_id)
    if not record:
        raise HTTPException(404, 'Resource not found')
    from sentinel.services import get_deposit
    get_deposit(db, actor, record.old_deposit_id, roles=['REVIEWER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.approve_replacement(db, actor, relationship_id, body, request.state.request_id))


class ClockCommand(StrictModel):
    as_of: date | None = None


@router.post('/monitoring/run')
def monitor(body: ClockCommand, request: Request, actor: Actor = Depends(authenticate),
            db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    ids = [i for i in actor.institution_ids() if actor.allows('REVIEWER', 'INSTITUTION', i)]
    if not ids:
        raise HTTPException(403, 'Reviewer scope required')
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: lifecycle.run_maturity(db, body.as_of or lifecycle.today(), ids,
                                                actor.subject, request.state.request_id))


@router.get('/notifications')
def notifications(actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    def delivery(notification):
        row = db.scalar(select(NotificationDelivery).where(NotificationDelivery.notification_id == notification.id))
        return {'id': row.id, 'state': row.state, 'attempts': row.attempts, 'last_error': row.last_error,
                'message_id': row.message_id, 'delivered_at': row.delivered_at.isoformat() if row.delivered_at else None} if row else None
    return [{'id': n.id, 'deposit_id': n.deposit_id, 'kind': n.kind, 'detail': n.detail,
             'delivery': delivery(n),
             'created_at': n.created_at.isoformat()}
            for n in db.scalars(select(Notification).where(Notification.institution_id.in_(
                actor.institution_ids())).order_by(Notification.created_at.desc()).limit(100))]


@router.post('/notifications/{notification_id}/retry')
def retry_notification(notification_id: str, body: VersionCommand, request: Request,
                       actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
                       idempotency_key: str | None = Header(None)):
    from sentinel.auth import require_scope
    from sentinel.transactions import audit
    row = db.get(Notification, notification_id)
    if not row:
        raise HTTPException(404, 'Notification not found')
    require_scope(actor, row.institution_id, ['REVIEWER'])
    def action():
        delivery = db.scalar(select(NotificationDelivery).where(NotificationDelivery.notification_id == row.id)
                             .with_for_update().execution_options(populate_existing=True))
        if not delivery or delivery.state != 'DEAD_LETTER' or delivery.attempts != body.expected_version:
            raise HTTPException(409, 'Stale or non-dead-letter notification')
        delivery.state, delivery.attempts, delivery.next_attempt_at = 'PENDING', 0, now()
        audit(db, row.institution_id, actor.subject, 'NOTIFICATION_RETRY_REQUESTED', row.deposit_id,
              {'notification_id': row.id}, request.state.request_id)
        return {'id': delivery.id, 'state': delivery.state}
    return mutate(db, actor, request, idempotency_key, body.model_dump(), action)
