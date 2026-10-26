"""Operational follow-up only. Source workflows remain the decision authority."""
import hashlib
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select, text
from sqlalchemy.dialects.postgresql import insert

from sentinel.delivery import ensure_delivery
from sentinel.models import (
    AuditEvent,
    ClearanceDecision,
    Deposit,
    Discrepancy,
    Document,
    Evaluation,
    Hold,
    Institution,
    IntegrationRequest,
    Intervention,
    Notification,
    OperationsPolicy,
    Principal,
    ReleaseCase,
    RoleBinding,
    now,
    uid,
)
from sentinel.transactions import audit

DEFAULTS = {'review_hours': 24, 'verification_hours': 2, 'discrepancy_hours': 24,
    'missing_document_hours': 24, 'clearance_hours': 48, 'escalation_hours': 24,
    'maturity_days': [90, 30, 7], 'supervisor_subject': None}
CATEGORIES = ('MISSING_DOCUMENTS', 'PENDING_VERIFICATION', 'OFFICER_REVIEW',
              'UNRESOLVED_DISCREPANCY', 'BUREAU_CLEARANCE', 'ACTIVE_HOLD',
              'MATURITY', 'REGULATORY_REVIEW')


def institution_lock(db, institution_id):
    key = int.from_bytes(hashlib.sha256(('operations:' + institution_id).encode()).digest()[:8], 'big', signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': key})


def current_policy(db, institution_id):
    row = db.scalar(select(OperationsPolicy).where(OperationsPolicy.institution_id == institution_id)
                    .order_by(OperationsPolicy.revision.desc()).limit(1))
    return ({**DEFAULTS, **row.configuration} if row else dict(DEFAULTS)), row.revision if row else 0


def active_bindings(db, institution_id, case_id=None):
    instant = now()  # Authorization always uses real time, including synthetic future-clock scans.
    scope = [((RoleBinding.scope_type == 'INSTITUTION') & (RoleBinding.scope_id == institution_id))]
    if case_id:
        scope.append((RoleBinding.scope_type == 'CASE') & (RoleBinding.scope_id == case_id))
    return db.scalars(select(RoleBinding).join(Principal).where(Principal.enabled.is_(True),
        RoleBinding.enabled.is_(True), RoleBinding.valid_from <= instant,
        or_(RoleBinding.valid_until.is_(None), RoleBinding.valid_until > instant), or_(*scope))).all()


def conditions(db, institution_id, config, instant):
    """Current source facts, including incomplete records; no mutation of business objects."""
    result = []
    deposits = db.scalars(select(Deposit).where(Deposit.institution_id == institution_id)).all()
    documents = db.scalars(select(Document).where(Document.institution_id == institution_id,
                                                   Document.active.is_(True))).all()
    completed = set(db.scalars(select(IntegrationRequest.deposit_id).where(
        IntegrationRequest.institution_id == institution_id, IntegrationRequest.operation == 'RELEASE_ACK',
        IntegrationRequest.state == 'SUCCEEDED')).all())
    # Only a successful sandbox completion retires its fictional maturity follow-up.
    completed = {r.deposit_id for r in db.scalars(select(IntegrationRequest).where(
        IntegrationRequest.deposit_id.in_(completed), IntegrationRequest.operation == 'RELEASE_ACK',
        IntegrationRequest.state == 'SUCCEEDED')) if (r.result or {}).get('outcome') == 'SANDBOX_COMPLETED'}
    def add(category, key, deposit, case, source_at, hours, detail):
        result.append({'category': category, 'condition_key': key,
            'deposit_id': deposit.id if deposit else None, 'case_id': case.id if case else None,
            'source_at': source_at, 'due_at': source_at + timedelta(hours=hours), 'detail': detail})
    for deposit in deposits:
        if deposit.lifecycle_status == 'REPLACED':
            continue
        proof = [d for d in documents if d.deposit_id == deposit.id and not d.release_case_id
                 and d.category == 'DEPOSIT_PROOF' and d.status == 'READY']
        if not proof:
            add('MISSING_DOCUMENTS', 'proof:' + deposit.id, deposit, None, deposit.created_at,
                config['missing_document_hours'], {'required': ['READY DEPOSIT_PROOF'],
                    'evidence': [{'id': d.id, 'status': d.status} for d in documents
                                 if d.deposit_id == deposit.id and not d.release_case_id]})
        if deposit.workflow == 'PENDING_SCRUTINY':
            submitted = db.scalar(select(func.max(AuditEvent.created_at)).where(
                AuditEvent.aggregate_id == deposit.id, AuditEvent.action.in_(
                    ['SUBMITTED_FOR_SCRUTINY', 'REGISTRATION_REVALIDATION_REQUESTED']))) or deposit.created_at
            add('OFFICER_REVIEW', f'review:{deposit.id}:{submitted.isoformat()}', deposit, None,
                submitted, config['review_hours'], {'workflow': deposit.workflow})
        if deposit.workflow != 'ACCEPTED':
            evaluation = db.scalar(select(Evaluation).where(Evaluation.deposit_id == deposit.id,
                Evaluation.input_revision == deposit.input_revision).order_by(Evaluation.evaluated_at.desc()).limit(1))
            unknowns = [f for f in evaluation.result['findings'] if f['code'] == 'UNSUPPORTED_CONTEXT'] if evaluation else []
            if unknowns:
                add('REGULATORY_REVIEW', f'policy:{deposit.id}:{deposit.input_revision}', deposit, None,
                    evaluation.evaluated_at, config['review_hours'], {'findings': unknowns,
                    'policy_revision': evaluation.policy_revision, 'authority': 'POLICY_OWNER_REVIEW_REQUIRED'})
        if deposit.maturity_date and deposit.id not in completed:
            deadline = datetime.combine(deposit.maturity_date, time.min, ZoneInfo('Asia/Kolkata'))
            if deadline <= instant + timedelta(days=max(config['maturity_days'])):
                add('MATURITY', f'maturity:{deposit.id}:{deposit.maturity_date}', deposit, None,
                    deadline, 0, {'maturity_date': str(deposit.maturity_date), 'no_automatic_release': True})
    by_id = {d.id: d for d in deposits}
    for discrepancy in db.scalars(select(Discrepancy).join(Deposit).where(
            Deposit.institution_id == institution_id, Discrepancy.status == 'OPEN')):
        if by_id[discrepancy.deposit_id].lifecycle_status != 'REPLACED':
            add('UNRESOLVED_DISCREPANCY', 'discrepancy:' + discrepancy.id, by_id[discrepancy.deposit_id], None,
                discrepancy.created_at, config['discrepancy_hours'], {'discrepancy_id': discrepancy.id,
                    'finding': discrepancy.finding, 'evaluation_id': discrepancy.evaluation_id})
    # Only the latest request per resource/operation represents current verification work.
    latest = {}
    for request in db.scalars(select(IntegrationRequest).where(IntegrationRequest.institution_id == institution_id)
                              .order_by(IntegrationRequest.created_at, IntegrationRequest.id)):
        latest[(request.deposit_id, request.case_id, request.operation)] = request
    for request in latest.values():
        deposit = by_id.get(request.deposit_id)
        if deposit and (deposit.input_revision != request.input_revision or deposit.lifecycle_status == 'REPLACED'):
            continue
        outcome = (request.result or {}).get('outcome')
        if request.state != 'SUCCEEDED' or outcome not in ('MATCH', 'CASE_RECEIVED', 'SANDBOX_COMPLETED'):
            add('PENDING_VERIFICATION', 'verification:' + request.id, deposit, db.get(ReleaseCase, request.case_id)
                if request.case_id else None, request.created_at, config['verification_hours'],
                {'request_id': request.id, 'operation': request.operation, 'state': request.state,
                 'outcome': outcome, 'requested_by': request.requested_by, 'last_error': request.last_error})
    from sentinel.lifecycle import BRANCH_EVIDENCE, RELEASE_CATEGORIES
    for case in db.scalars(select(ReleaseCase).where(ReleaseCase.institution_id == institution_id,
                                                    ReleaseCase.state != 'ISSUED_SYNTHETIC')):
        ready = {d.category for d in documents if d.release_case_id == case.id and d.status == 'READY'}
        required = RELEASE_CATEGORIES | ({BRANCH_EVIDENCE[case.reason]} if case.reason in BRANCH_EVIDENCE else set())
        missing = sorted(required - ready)
        if missing:
            add('MISSING_DOCUMENTS', f'case-proof:{case.id}:{case.input_revision}', by_id[case.deposit_id], case,
                case.created_at, config['missing_document_hours'], {'required': missing})
        if case.state in ('CLEARANCES_PENDING', 'APPROVAL_REVIEW', 'APPROVED_SYNTHETIC'):
            submitted = db.scalar(select(func.max(AuditEvent.created_at)).where(AuditEvent.aggregate_id == case.id,
                AuditEvent.action == 'RELEASE_SUBMITTED_SYNTHETIC')) or case.created_at
            cleared = {c.bureau for c in db.scalars(select(ClearanceDecision).where(
                ClearanceDecision.case_id == case.id, ClearanceDecision.input_revision == case.input_revision,
                ClearanceDecision.decision == 'CLEARED'))}
            for bureau in sorted(set(case.required_bureaus) - cleared):
                add('BUREAU_CLEARANCE', f'clearance:{case.id}:{case.input_revision}:{bureau}', by_id[case.deposit_id],
                    case, submitted, config['clearance_hours'], {'bureau': bureau, 'state': case.state})
        for hold in db.scalars(select(Hold).where(Hold.case_id == case.id, Hold.active.is_(True))):
            add('ACTIVE_HOLD', 'hold:' + hold.id, by_id[case.deposit_id], case, hold.created_at,
                config['clearance_hours'], {'hold_id': hold.id, 'kind': hold.kind, 'reason': hold.reason})
    return result


def notify(db, task, recipients, stage, instant, actor, request_id):
    count = 0
    for recipient in sorted(set(recipients)):
        identity = db.execute(insert(Notification).values(id=uid(), institution_id=task.institution_id,
            deposit_id=task.deposit_id, dedupe_key=f'ops:{task.id}:{stage}:{hashlib.sha256(recipient.encode()).hexdigest()}', recipient=recipient,
            kind='OPERATIONS_' + stage, detail={'intervention_id': task.id, 'category': task.category,
                'stage': stage, 'due_at': task.due_at.isoformat(), 'observed_at': instant.isoformat(),
                'policy_revision': task.policy_revision, 'case_id': task.case_id,
                'basis': 'PRODUCT_SLA_NOT_STATUTORY', 'no_automatic_approval': True})
            .on_conflict_do_nothing().returning(Notification.id)).scalar_one_or_none()
        if identity:
            ensure_delivery(db, identity)
            count += 1
            audit(db, task.institution_id, actor, 'OPERATIONS_' + stage, task.id,
                  {'notification_id': identity, 'recipient': recipient}, request_id)
    return count


def scan(db, institution_ids, instant=None, actor='operations-worker', request_id='scheduled'):
    instant = instant or now()
    totals = {'created': 0, 'resolved': 0, 'notifications': 0, 'as_of': instant.isoformat(),
              'basis': 'PRODUCT_SLA_NOT_STATUTORY', 'no_automatic_approval': True}
    for institution_id in sorted(set(institution_ids)):
        institution_lock(db, institution_id)
        config, revision = current_policy(db, institution_id)
        current = conditions(db, institution_id, config, instant)
        keys = {c['condition_key'] for c in current}
        opened = {t.condition_key: t for t in db.scalars(select(Intervention).where(
            Intervention.institution_id == institution_id, Intervention.state == 'OPEN').with_for_update())}
        for key, task in opened.items():
            if key not in keys:
                task.state, task.resolved_at = 'RESOLVED', instant
                totals['resolved'] += 1
                audit(db, institution_id, actor, 'INTERVENTION_SOURCE_RESOLVED', task.id,
                      {'condition_key': key, 'as_of': instant.isoformat()}, request_id)
        for fact in current:
            task = opened.get(fact['condition_key'])
            if not task:
                episode = (db.scalar(select(func.max(Intervention.episode)).where(
                    Intervention.institution_id == institution_id,
                    Intervention.condition_key == fact['condition_key'])) or 0) + 1
                task = Intervention(id=uid(), institution_id=institution_id, episode=episode,
                    policy_revision=revision, observed_at=instant, state='OPEN', **fact)
                db.add(task)
                db.flush()
                totals['created'] += 1
                audit(db, institution_id, actor, 'INTERVENTION_OPENED', task.id,
                      {'category': task.category, 'condition_key': task.condition_key}, request_id)
            else:
                task.due_at, task.detail, task.policy_revision, task.observed_at = (
                    fact['due_at'], fact['detail'], revision, instant)
            if instant < task.due_at:
                continue
            bindings = active_bindings(db, institution_id, task.case_id)
            roles = {'REVIEWER'}
            if task.category in ('MISSING_DOCUMENTS', 'UNRESOLVED_DISCREPANCY', 'MATURITY'):
                roles.add('MAKER')
            recipients = [b.subject for b in bindings if b.role in roles]
            if task.category == 'BUREAU_CLEARANCE':
                bureau = task.detail['bureau']
                for binding in bindings:
                    if binding.role == 'CLEARANCE' and db.scalar(select(RoleBinding.id).where(
                        RoleBinding.subject == binding.subject, RoleBinding.role == 'CLEARANCE',
                        RoleBinding.scope_type == 'BUREAU', RoleBinding.scope_id == bureau,
                        RoleBinding.enabled.is_(True), RoleBinding.valid_from <= now(),
                        or_(RoleBinding.valid_until.is_(None), RoleBinding.valid_until > now()))):
                        recipients.append(binding.subject)
            totals['notifications'] += notify(db, task, recipients, 'REMINDER', instant, actor, request_id)
            supervisor = config['supervisor_subject']
            if supervisor and instant >= task.due_at + timedelta(hours=config['escalation_hours']):
                # Existing independent scope is rechecked each run; assignment revocation is effective immediately.
                authorized = any(b.subject == supervisor and b.role in ('REVIEWER', 'AUDITOR', 'APPROVER')
                                 for b in bindings)
                if authorized:
                    totals['notifications'] += notify(db, task, [supervisor], 'ESCALATION', instant, actor, request_id)
        db.flush()
    return totals


def scan_all(db):
    return scan(db, db.scalars(select(Institution.id)).all())
