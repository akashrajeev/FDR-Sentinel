import csv
import io
import statistics
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from sentinel.auth import Actor, authenticate
from sentinel.compliance import POLICY, POLICY_REVISION
from sentinel.db import get_db
from sentinel.lifecycle import today
from sentinel.models import AuditEvent, Deposit, Institution, ReleaseCase
from sentinel.schemas import DepositOut, SummaryOut, VersionCommand
from sentinel.services import check_version, dto, get_deposit
from sentinel.transactions import audit, mutate

router = APIRouter(prefix='/api/v1')


def scoped_deposits(actor):
    case_ids = select(ReleaseCase.deposit_id).where(ReleaseCase.id.in_(actor.case_ids()))
    return or_(Deposit.institution_id.in_(actor.institution_ids()), Deposit.id.in_(case_ids))


@router.get('/policies/current')
def policy(actor: Actor = Depends(authenticate)):
    return {'policy': POLICY, 'checksum': POLICY_REVISION, 'production_activation': 'BLOCKED_PENDING_OWNER_REVIEW'}


@router.post('/deposits/{deposit_id}/request-revalidation', response_model=DepositOut)
def revalidate(deposit_id: str, body: VersionCommand, request: Request, actor: Actor = Depends(authenticate),
               db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    get_deposit(db, actor, deposit_id, roles=['MAKER', 'REVIEWER'])
    def action():
        deposit = get_deposit(db, actor, deposit_id, lock=True, roles=['MAKER', 'REVIEWER'])
        check_version(deposit, body.expected_version, ['ACCEPTED'])
        deposit.workflow = 'PENDING_SCRUTINY'
        deposit.version += 1
        case = db.scalar(select(ReleaseCase).where(ReleaseCase.deposit_id == deposit.id).with_for_update())
        if case and case.state != 'ISSUED_SYNTHETIC':
            case.state = 'DRAFT'
            case.version += 1
            case.input_revision += 1
            case.approver = None
            case.regulatory_basis = None
            case.submitted_document_hash = None
            audit(db, deposit.institution_id, actor.subject, 'RELEASE_REVALIDATION_REQUIRED', case.id,
                  {'policy_revision': POLICY_REVISION, 'prior_clearances_invalidated': True}, request.state.request_id)
        audit(db, deposit.institution_id, actor.subject, 'REGISTRATION_REVALIDATION_REQUESTED', deposit.id,
              {'policy_revision': POLICY_REVISION, 'prior_review_preserved': True}, request.state.request_id)
        return dto(deposit, DepositOut)
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)


@router.get('/search/deposits', response_model=list[DepositOut])
def search(q: str = Query('', max_length=100), workflow: str | None = None,
           after: str | None = None, limit: int = Query(50, ge=1, le=100),
           actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    query = select(Deposit).join(Institution).where(scoped_deposits(actor))
    if q:
        query = query.where(or_(Institution.legal_name.ilike('%' + q + '%'), Deposit.bank_code.ilike('%' + q + '%'),
                               Deposit.reference_last4 == q[-4:].upper(), Deposit.id.startswith(q)))
    if workflow:
        if workflow not in ('DRAFT', 'PENDING_SCRUTINY', 'ACCEPTED'):
            raise HTTPException(422, 'Invalid workflow filter')
        query = query.where(Deposit.workflow == workflow)
    if after:
        query = query.where(Deposit.id > after)
    return [dto(d, DepositOut) for d in db.scalars(query.order_by(Deposit.id).limit(limit))]


@router.get('/dashboard/summary', response_model=SummaryOut)
def summary(actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    as_of = today()
    counts = dict(db.execute(select(Deposit.workflow, func.count()).where(scoped_deposits(actor))
                             .group_by(Deposit.workflow)).all())
    maturity = dict(db.execute(select(Deposit.lifecycle_status, func.count()).where(scoped_deposits(actor))
                               .group_by(Deposit.lifecycle_status)).all())
    total = db.scalar(select(func.coalesce(func.sum(Deposit.amount_paise), 0)).where(scoped_deposits(actor)))
    matured = db.scalar(select(func.count()).select_from(Deposit).where(scoped_deposits(actor),
        Deposit.lifecycle_status != 'REPLACED', Deposit.maturity_date <= as_of))
    upcoming = db.scalar(select(func.count()).select_from(Deposit).where(scoped_deposits(actor),
        Deposit.lifecycle_status != 'REPLACED', Deposit.maturity_date > as_of,
        Deposit.maturity_date <= as_of + timedelta(days=90)))
    cases = dict(db.execute(select(ReleaseCase.state, func.count()).where(or_(
        ReleaseCase.institution_id.in_(actor.institution_ids()), ReleaseCase.id.in_(actor.case_ids())))
        .group_by(ReleaseCase.state)).all())
    durations = db.execute(select(ReleaseCase.created_at, AuditEvent.created_at).join(
        AuditEvent, AuditEvent.aggregate_id == ReleaseCase.id).where(
            or_(ReleaseCase.institution_id.in_(actor.institution_ids()), ReleaseCase.id.in_(actor.case_ids())),
            AuditEvent.action.in_(['SYNTHETIC_NOC_ISSUED', 'SYNTHETIC_SANCTION_ORDER_ISSUED']))).all()
    seconds = [(end - start).total_seconds() for start, end in durations]
    return {'as_of': as_of.isoformat(), 'mode': 'SYNTHETIC_LOCAL', 'workflow_counts': counts,
            'stored_lifecycle_counts': maturity, 'declared_total_paise': str(total),
            'fdr_matured_from_dates': matured, 'fdr_upcoming_90_days': upcoming, 'release_case_counts': cases,
            'actual_financial_releases': 0, 'external_verification': 'NOT_CONNECTED',
            'completed_synthetic_case_time': {'samples': len(seconds),
                'median_seconds': round(statistics.median(seconds), 3) if seconds else None,
                'basis': 'CREATE_TO_SYNTHETIC_ISSUANCE_AUDIT_TIMESTAMPS; AUTOMATED_DEMO_NOT_HUMAN_TURNAROUND'},
            'policy_revision': POLICY_REVISION, 'policy_status': POLICY['activation']}


def csv_safe(value):
    text = str(value)
    probe = text.lstrip('\ufeff \t\r\n')
    return "'" + text if probe.startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r')) else text


@router.get('/reports/deposits.csv')
def export(request: Request, actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['mode', 'deposit_id', 'institution', 'type', 'amount_paise', 'reference_last4',
                     'workflow', 'verification', 'lifecycle', 'maturity_date'])
    # Export is separately capped to avoid silently presenting a partial 100-row list as a full report.
    query = select(Deposit, Institution.legal_name).join(Institution).where(scoped_deposits(actor)).order_by(
        Deposit.id).limit(10001)
    rows = db.execute(query).all()
    if len(rows) > 10000:
        raise HTTPException(409, 'Export exceeds 10000 rows; request a bounded reporting job')
    tenant_ids = set()
    for deposit, name in rows:
        tenant_ids.add(deposit.institution_id)
        writer.writerow([csv_safe(v) for v in ['SYNTHETIC', deposit.id, name, deposit.deposit_type,
            deposit.amount_paise, deposit.reference_last4, deposit.workflow, deposit.verification_status,
            deposit.lifecycle_status, deposit.maturity_date or '']])
    for institution_id in tenant_ids:
        audit(db, institution_id, actor.subject, 'SCOPED_REPORT_EXPORTED', institution_id,
              {'type': 'DEPOSITS_CSV', 'rows_total': len(rows), 'synthetic': True}, request.state.request_id)
    db.commit()
    return Response(output.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': 'attachment; filename="synthetic-deposits.csv"'})
