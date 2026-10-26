import csv
import io
import json
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import Field, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from sentinel import operations
from sentinel.auth import Actor, authenticate, require_scope
from sentinel.config import settings
from sentinel.db import get_db
from sentinel.models import Intervention, Notification, NotificationDelivery, OperationsPolicy, now
from sentinel.reporting_api import csv_safe
from sentinel.schemas import StrictModel
from sentinel.transactions import audit, mutate

router = APIRouter(prefix='/api/v1')


class OperationsSettings(StrictModel):
    expected_revision: int = Field(ge=0)
    review_hours: int = Field(default=24, ge=1, le=8760)
    verification_hours: int = Field(default=2, ge=1, le=8760)
    discrepancy_hours: int = Field(default=24, ge=1, le=8760)
    missing_document_hours: int = Field(default=24, ge=1, le=8760)
    clearance_hours: int = Field(default=48, ge=1, le=8760)
    escalation_hours: int = Field(default=24, ge=1, le=8760)
    maturity_days: list[int] = Field(default=[90, 30, 7], min_length=1, max_length=8)
    supervisor_subject: str | None = Field(default=None, max_length=128)
    reason: str = Field(min_length=10, max_length=2000)

    @model_validator(mode='after')
    def thresholds(self):
        if any(type(d) is not int or not 1 <= d <= 730 for d in self.maturity_days):
            raise ValueError('Maturity reminder days must be integers between 1 and 730')
        self.maturity_days = sorted(set(self.maturity_days), reverse=True)
        return self


class ScanCommand(StrictModel):
    institution_id: str = Field(min_length=1, max_length=36)
    as_of: datetime | None = None


class Acknowledgement(StrictModel):
    reason: str = Field(min_length=10, max_length=2000)


@router.get('/institutions/{institution_id}/operations-policy')
def policy(institution_id: str, actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    require_scope(actor, institution_id)
    config, revision = operations.current_policy(db, institution_id)
    candidates = sorted({b.subject for b in operations.active_bindings(db, institution_id)
                         if b.role in ('REVIEWER', 'AUDITOR', 'APPROVER') and b.subject != actor.subject})
    return {'configuration': config, 'revision': revision, 'supervisor_candidates': candidates,
            'basis': 'PRODUCT_SLA_NOT_STATUTORY'}


@router.post('/institutions/{institution_id}/operations-policy')
def configure(institution_id: str, body: OperationsSettings, request: Request,
              actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
              idempotency_key: str | None = Header(None)):
    require_scope(actor, institution_id, ['REVIEWER'])
    def action():
        operations.institution_lock(db, institution_id)
        _, revision = operations.current_policy(db, institution_id)
        if revision != body.expected_revision:
            raise HTTPException(409, 'Operations policy changed; reload before editing')
        if body.supervisor_subject and (body.supervisor_subject == actor.subject or not any(
            b.subject == body.supervisor_subject and b.role in ('REVIEWER', 'AUDITOR', 'APPROVER')
            for b in operations.active_bindings(db, institution_id))):
            raise HTTPException(422, 'Supervisor must be a different active scoped officer/auditor')
        config = body.model_dump(exclude={'expected_revision', 'reason'})
        row = OperationsPolicy(institution_id=institution_id, revision=revision + 1,
            configuration=config, actor=actor.subject, reason=body.reason)
        db.add(row)
        db.flush()
        audit(db, institution_id, actor.subject, 'OPERATIONS_POLICY_CHANGED', row.id,
              {'revision': row.revision, 'configuration': config, 'reason': body.reason,
               'basis': 'PRODUCT_SLA_NOT_STATUTORY'}, request.state.request_id)
        return {'configuration': config, 'revision': row.revision}
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)


@router.post('/operations/scan')
def scan(body: ScanCommand, request: Request, actor: Actor = Depends(authenticate),
         db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    require_scope(actor, body.institution_id, ['REVIEWER'])
    if body.as_of and (not body.as_of.tzinfo or not settings().synthetic_mode):
        raise HTTPException(422, 'Timezone-aware clock override is restricted to synthetic mode')
    if body.as_of and not now() - timedelta(days=3650) <= body.as_of <= now() + timedelta(days=3650):
        raise HTTPException(422, 'Synthetic clock must remain within ten years of real time')
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
        lambda: operations.scan(db, [body.institution_id], body.as_of, actor.subject, request.state.request_id))


def scoped(actor):
    return or_(Intervention.institution_id.in_(actor.institution_ids()), Intervention.case_id.in_(actor.case_ids()))


def task_out(row):
    return {key: getattr(row, key) for key in ('id', 'institution_id', 'deposit_id', 'case_id', 'category',
        'state', 'episode', 'source_at', 'due_at', 'observed_at', 'policy_revision', 'detail',
        'resolved_at', 'acknowledged_by', 'acknowledged_at', 'acknowledgement')}


@router.get('/reports/interventions')
def report(category: str | None = None, state: Literal['OPEN', 'RESOLVED', 'ALL'] = 'OPEN',
           institution_id: str | None = None, deposit_id: str | None = None, overdue: bool = False, after: str | None = None,
           limit: int = Query(50, ge=1, le=100), actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    if category and category not in operations.CATEGORIES:
        raise HTTPException(422, 'Unknown intervention category')
    filters = [scoped(actor)]
    if state != 'ALL':
        filters.append(Intervention.state == state)
    if category:
        filters.append(Intervention.category == category)
    if institution_id:
        filters.append(Intervention.institution_id == institution_id)
    if deposit_id:
        filters.append(Intervention.deposit_id == deposit_id)
    if overdue:
        filters.append(Intervention.due_at <= now())
    counts = dict(db.execute(select(Intervention.category, func.count()).where(*filters)
                             .group_by(Intervention.category)).all())
    query = select(Intervention).where(*filters)
    if after:
        query = query.where(Intervention.id > after)
    rows = db.scalars(query.order_by(Intervention.id).limit(limit + 1)).all()
    return {'items': [task_out(t) for t in rows[:limit]], 'counts': counts, 'total': sum(counts.values()),
            'next_cursor': rows[limit - 1].id if len(rows) > limit else None, 'as_of': now(),
            'basis': 'PRODUCT_SLA_NOT_STATUTORY', 'categories': operations.CATEGORIES}


@router.get('/reports/interventions.csv')
def export(request: Request, category: str | None = None, state: Literal['OPEN', 'RESOLVED', 'ALL'] = 'OPEN',
           institution_id: str | None = None, deposit_id: str | None = None,
           overdue: bool = False,
           actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    if category and category not in operations.CATEGORIES:
        raise HTTPException(422, 'Unknown intervention category')
    filters = [scoped(actor)]
    if category:
        filters.append(Intervention.category == category)
    if state != 'ALL':
        filters.append(Intervention.state == state)
    if institution_id:
        filters.append(Intervention.institution_id == institution_id)
    if deposit_id:
        filters.append(Intervention.deposit_id == deposit_id)
    if overdue:
        filters.append(Intervention.due_at <= now())
    rows = db.scalars(select(Intervention).where(*filters).order_by(Intervention.id).limit(10001)).all()
    if len(rows) > 10000:
        raise HTTPException(409, 'Export exceeds 10000 rows; narrow filters')
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['mode', 'id', 'institution_id', 'deposit_id', 'case_id', 'category', 'state',
                     'source_at', 'due_at', 'observed_at', 'policy_revision', 'acknowledged_by', 'detail'])
    for row in rows:
        writer.writerow([csv_safe(v if v is not None else '') for v in ['SYNTHETIC_PRODUCT_SLA', row.id,
            row.institution_id, row.deposit_id, row.case_id, row.category, row.state, row.source_at, row.due_at,
            row.observed_at, row.policy_revision, row.acknowledged_by, json.dumps(row.detail, sort_keys=True)]])
    for tenant in sorted({r.institution_id for r in rows}):
        audit(db, tenant, actor.subject, 'INTERVENTION_REPORT_EXPORTED', tenant,
              {'rows_total': len(rows), 'category': category, 'state': state}, request.state.request_id)
    db.commit()
    return Response(output.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': 'attachment; filename="synthetic-interventions.csv"'})


@router.post('/interventions/{identity}/acknowledge')
def acknowledge(identity: str, body: Acknowledgement, request: Request, actor: Actor = Depends(authenticate),
                db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    row = db.scalar(select(Intervention).where(Intervention.id == identity, scoped(actor)))
    if not row:
        raise HTTPException(404, 'Resource not found')
    require_scope(actor, row.institution_id, ['REVIEWER'])
    def action():
        task = db.scalar(select(Intervention).where(Intervention.id == identity).with_for_update())
        if task.state != 'OPEN' or task.acknowledged_at:
            raise HTTPException(409, 'Only an unacknowledged open intervention can be acknowledged')
        task.acknowledged_by, task.acknowledged_at, task.acknowledgement = actor.subject, now(), body.reason
        audit(db, task.institution_id, actor.subject, 'INTERVENTION_ACKNOWLEDGED', task.id,
              {'reason': body.reason, 'does_not_resolve_source': True}, request.state.request_id)
        return task_out(task)
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)


@router.get('/interventions/{identity}/notifications')
def notifications(identity: str, actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    task = db.scalar(select(Intervention).where(Intervention.id == identity, scoped(actor)))
    if not task:
        raise HTTPException(404, 'Resource not found')
    rows = db.execute(select(Notification, NotificationDelivery).outerjoin(NotificationDelivery,
        NotificationDelivery.notification_id == Notification.id).where(
            Notification.dedupe_key.startswith('ops:' + identity + ':')).order_by(Notification.created_at)).all()
    return [{'id': n.id, 'kind': n.kind, 'recipient': n.recipient, 'detail': n.detail,
             'delivery': {'state': d.state, 'attempts': d.attempts, 'last_error': d.last_error} if d else None}
            for n, d in rows]
