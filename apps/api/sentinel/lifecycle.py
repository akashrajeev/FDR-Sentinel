"""Human-governed lifecycle services. Issuance here is exclusively synthetic."""
import hashlib
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pymupdf
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from sentinel.auth import require_decision_assurance
from sentinel.compliance import POLICY, POLICY_REVISION, document_set_hash
from sentinel.config import settings
from sentinel.models import (
    ClearanceDecision,
    Deposit,
    Document,
    Hold,
    Notification,
    Outbox,
    ReleaseCase,
    Replacement,
    ReviewDecision,
    uid,
)
from sentinel.schemas import DocumentOut
from sentinel.services import check_version, current_evaluation, documents_for, dto, get_deposit
from sentinel.storage import put_original
from sentinel.telemetry import capture_context
from sentinel.transactions import audit

RELEASE_CATEGORIES = {'REQUEST_LETTER', 'AFFIDAVIT_6', 'APPROVAL_LETTER'}
OPTIONAL_RELEASE_CATEGORIES = {'EXTERNAL_BODY_NOC'}
BRANCH_EVIDENCE = {'CLOSURE': 'CLOSURE_ORDER', 'MERGER': 'MERGER_ORDER',
                   'CONVERSION': 'CONVERSION_ORDER', 'OTHER': 'SUPPORTING'}


def today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()


def get_case(db, actor, case_id, lock=False, roles=None):
    case = db.get(ReleaseCase, case_id)
    if not case:
        raise HTTPException(404, 'Resource not found')
    # Always lock deposit before case for consistent lock ordering with document workers.
    if case.institution_id in actor.institution_ids():
        get_deposit(db, actor, case.deposit_id, lock=lock, roles=roles)
    elif case.id in actor.case_ids(roles):
        query = select(Deposit).where(Deposit.id == case.deposit_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        db.scalar(query)
    else:
        raise HTTPException(404, 'Resource not found')
    if lock:
        case = db.scalar(select(ReleaseCase).where(ReleaseCase.id == case_id).with_for_update()
                         .execution_options(populate_existing=True))
    return case


def case_documents(db, case):
    return db.scalars(select(Document).where(Document.release_case_id == case.id,
                     Document.active.is_(True), Document.category != 'SYNTHETIC_OUTPUT')).all()


def clearances(db, case):
    return db.scalars(select(ClearanceDecision).where(ClearanceDecision.case_id == case.id,
                     ClearanceDecision.input_revision == case.input_revision)).all()


def holds(db, case):
    return db.scalars(select(Hold).where(Hold.case_id == case.id)).all()


def case_evidence(db, case):
    return [*documents_for(db, db.get(Deposit, case.deposit_id)), *case_documents(db, case)]


def blockers(db, case):
    decisions = {c.bureau: c.decision for c in clearances(db, case)}
    results = [f'{bureau} clearance {decisions.get(bureau, "PENDING")}'
               for bureau in case.required_bureaus if decisions.get(bureau) != 'CLEARED']
    results += [f'HOLD: {h.reason}' for h in holds(db, case) if h.active]
    return results


def case_detail(db, case):
    return {'id': case.id, 'deposit_id': case.deposit_id, 'institution_id': case.institution_id,
            'reason': case.reason, 'policy_revision': case.policy_revision, 'state': case.state, 'version': case.version,
            'input_revision': case.input_revision, 'required_bureaus': case.required_bureaus,
            'approver': case.approver, 'issuer': case.issuer, 'output_document_id': case.output_document_id,
            'clearances': [{'bureau': c.bureau, 'decision': c.decision, 'actor': c.actor,
                            'reason': c.reason, 'evidence_document_id': c.evidence_document_id}
                           for c in clearances(db, case)],
            'holds': [{'id': h.id, 'reason': h.reason, 'kind': h.kind, 'required_category': h.required_category,
                       'active': h.active, 'resolution': h.resolution}
                      for h in holds(db, case)],
            'documents': [dto(d, DocumentOut) for d in case_evidence(db, case)],
            'blockers': blockers(db, case), 'mode': 'SYNTHETIC_ONLY_NO_FINANCIAL_AUTHORITY'}


def case_version(case, expected, states=None):
    if case.version != expected:
        raise HTTPException(409, 'Stale release case version')
    if states and case.state not in states:
        raise HTTPException(409, f'Operation unavailable in {case.state}')


def create_case(db, actor, body, request_id):
    deposit = get_deposit(db, actor, body.deposit_id, lock=True, roles=['MAKER'])
    if deposit.workflow != 'ACCEPTED' or deposit.lifecycle_status == 'REPLACED':
        raise HTTPException(409, 'Accepted, unreplaced deposit required')
    if body.reason == 'TERM_COMPLETED':
        if deposit.deposit_type == 'FDR' and deposit.maturity_date > today():
            raise HTTPException(409, 'FDR has not matured; maturity still does not imply eligibility')
    case = ReleaseCase(deposit_id=deposit.id, institution_id=deposit.institution_id,
                       reason=body.reason, maker=actor.subject, policy_revision=POLICY_REVISION,
                       required_bureaus=list(POLICY['release_minimum_bureaus']))
    db.add(case)
    db.flush()
    if body.reason in BRANCH_EVIDENCE:
        db.add(Hold(case_id=case.id, authority='policy-engine',
                    kind='REGULATORY_EXCEPTION', required_category=BRANCH_EVIDENCE[body.reason],
                    reason=f'{body.reason}: additional evidence and human policy applicability review required'))
        db.flush()
    audit(db, deposit.institution_id, actor.subject, 'RELEASE_CASE_CREATED', case.id,
          {'reason': body.reason, 'synthetic_only': True}, request_id)
    return case_detail(db, case)


def upload_case_document(db, actor, case_id, data, category, request_id):
    case = get_case(db, actor, case_id, lock=True, roles=['MAKER'])
    case_version(case, case.version, ['DRAFT'])
    if category not in RELEASE_CATEGORIES | OPTIONAL_RELEASE_CATEGORIES | set(BRANCH_EVIDENCE.values()):
        raise HTTPException(422, 'Unsupported release evidence category')
    if len(case_documents(db, case)) >= 20:
        raise HTTPException(409, 'Release evidence limit reached')
    document_id = uid()
    key = f'originals/{case.institution_id}/{document_id}.pdf'
    try:
        put_original(key, data)
    except Exception:
        raise HTTPException(503, 'Private storage unavailable') from None
    document = Document(id=document_id, deposit_id=case.deposit_id, institution_id=case.institution_id,
                        release_case_id=case.id, category=category, object_key=key,
                        sha256=hashlib.sha256(data).hexdigest(), size=len(data), uploader=actor.subject)
    db.add(document)
    db.flush()
    db.add(Outbox(aggregate_id=document.id, trace_context=capture_context()))
    case.version += 1
    case.input_revision += 1
    audit(db, case.institution_id, actor.subject, 'RELEASE_EVIDENCE_QUARANTINED', case.id,
          {'document_id': document.id, 'sha256': document.sha256}, request_id)
    return dto(document, DocumentOut)


def validate_case_evidence(db, case):
    deposit = db.get(Deposit, case.deposit_id)
    if case.reason == 'TERM_COMPLETED' and deposit.deposit_type in ('RTGS', 'ONLINE'):
        # Calendar anniversary, not 3650 days; leap-day deposits mature on Feb 28.
        deposited = deposit.deposited_on
        if not deposited:
            raise HTTPException(409, 'Online deposit term evidence is missing')
        try:
            anniversary = deposited.replace(year=deposited.year + 10)
        except ValueError:
            anniversary = deposited.replace(year=deposited.year + 10, day=28)
        if today() < anniversary:
            raise HTTPException(409, 'Online/RTGS ten-year term has not elapsed; use applicable exception review')
    documents = case_evidence(db, case)
    required = RELEASE_CATEGORIES | {'DEPOSIT_PROOF'}
    if case.reason in BRANCH_EVIDENCE:
        required |= {BRANCH_EVIDENCE[case.reason]}
    available = {d.category for d in documents if d.status == 'READY'}
    missing = required - available
    if missing:
        raise HTTPException(409, 'Incomplete release evidence: ' + ', '.join(sorted(missing)))
    if any(d.status != 'READY' for d in documents):
        raise HTTPException(409, 'Release evidence must finish safe processing')
    return document_set_hash(documents)


def submit_case(db, actor, case_id, body, request_id):
    case = get_case(db, actor, case_id, lock=True, roles=['MAKER'])
    case_version(case, body.expected_version, ['DRAFT'])
    deposit = db.get(Deposit, case.deposit_id)
    evaluation = current_evaluation(db, deposit)
    if deposit.workflow != 'ACCEPTED' or evaluation.result['outcome'] == 'FAIL':
        raise HTTPException(409, 'Registration review must be complete without unresolved blockers')
    case.submitted_document_hash = validate_case_evidence(db, case)
    case.policy_revision = POLICY_REVISION
    case.state = 'CLEARANCES_PENDING'
    case.version += 1
    audit(db, case.institution_id, actor.subject, 'RELEASE_SUBMITTED_SYNTHETIC', case.id,
          {'document_set_hash': case.submitted_document_hash, 'required_bureaus': case.required_bureaus}, request_id)
    return case_detail(db, case)


def evidence_in_case(db, case, document_id):
    document = db.get(Document, document_id)
    if (not document or document.deposit_id != case.deposit_id or document.status != 'READY'
            or not document.active or document.release_case_id not in (None, case.id)):
        raise HTTPException(409, 'Scoped READY evidence required')
    return document


def decide_clearance(db, actor, case_id, bureau, body, request_id):
    case = get_case(db, actor, case_id, lock=True)
    if not actor.allows('CLEARANCE', 'BUREAU', bureau):
        raise HTTPException(403, 'Actor cannot decide for this bureau')
    case_version(case, body.expected_version, ['CLEARANCES_PENDING'])
    if bureau not in case.required_bureaus:
        raise HTTPException(422, 'Bureau is not required by this case')
    prior = clearances(db, case)
    conflicting_history = db.scalar(select(ClearanceDecision.id).where(
        ClearanceDecision.case_id == case.id, ClearanceDecision.actor == actor.subject,
        ClearanceDecision.bureau != bureau))
    if actor.subject in (case.maker, db.get(Deposit, case.deposit_id).maker) or conflicting_history:
        raise HTTPException(403, 'Independent bureau actor required; maker cannot clear')
    if any(c.bureau == bureau for c in prior):
        raise HTTPException(409, 'Bureau decision already recorded; no silent overwrite')
    evidence_in_case(db, case, body.evidence_document_id)
    db.add(ClearanceDecision(case_id=case.id, bureau=bureau, input_revision=case.input_revision, actor=actor.subject,
                             decision=body.decision, reason=body.reason,
                             evidence_document_id=body.evidence_document_id))
    db.flush()
    if body.decision == 'REJECTED':
        db.add(Hold(case_id=case.id, authority=actor.subject, reason=f'{bureau} rejected: {body.reason}'))
        db.flush()
    if all(c.decision == 'CLEARED' for c in clearances(db, case)) and len(clearances(db, case)) == len(case.required_bureaus):
        case.state = 'APPROVAL_REVIEW'
    case.version += 1
    audit(db, case.institution_id, actor.subject, 'BUREAU_' + body.decision, case.id,
          {'bureau': bureau, 'evidence_document_id': body.evidence_document_id, 'reason': body.reason}, request_id)
    return case_detail(db, case)


def add_hold(db, actor, case_id, body, request_id):
    case = get_case(db, actor, case_id, lock=True, roles=['REVIEWER', 'APPROVER'])
    case_version(case, body.expected_version)
    if case.state == 'ISSUED_SYNTHETIC':
        raise HTTPException(409, 'Already issued; requires separate incident/revocation process')
    db.add(Hold(case_id=case.id, authority=actor.subject, reason=body.reason, kind=body.kind,
                required_category='EXTERNAL_BODY_NOC' if body.kind == 'FINANCIAL_EMBEZZLEMENT' else None))
    if case.state == 'APPROVED_SYNTHETIC':
        case.state = 'APPROVAL_REVIEW'
        case.approver = None
        case.regulatory_basis = None
    case.version += 1
    db.flush()
    audit(db, case.institution_id, actor.subject, 'RELEASE_HOLD_ADDED', case.id,
          {'reason': body.reason}, request_id)
    return case_detail(db, case)


def return_case(db, actor, case_id, body, request_id):
    case = get_case(db, actor, case_id, lock=True, roles=['REVIEWER'])
    case_version(case, body.expected_version, ['CLEARANCES_PENDING', 'APPROVAL_REVIEW'])
    if actor.subject == case.maker:
        raise HTTPException(403, 'Independent review required')
    case.state = 'DRAFT'
    case.input_revision += 1
    case.version += 1
    case.submitted_document_hash = None
    audit(db, case.institution_id, actor.subject, 'RELEASE_RETURNED_FOR_CORRECTION', case.id,
          {'reason': body.reason, 'input_revision': case.input_revision,
           'prior_clearances_retained_but_invalidated': True}, request_id)
    return case_detail(db, case)


def resolve_hold(db, actor, case_id, hold_id, body, request_id):
    case = get_case(db, actor, case_id, lock=True, roles=['APPROVER'])
    case_version(case, body.expected_version)
    hold = db.get(Hold, hold_id)
    if not hold or hold.case_id != case.id or not hold.active:
        raise HTTPException(409, 'Active case hold required')
    document = evidence_in_case(db, case, body.evidence_document_id)
    if hold.authority == 'policy-engine' and document.category != BRANCH_EVIDENCE.get(case.reason):
        raise HTTPException(409, 'Branch-specific order/evidence required to resolve policy hold')
    if hold.required_category and document.category != hold.required_category:
        raise HTTPException(409, f'{hold.required_category} is required to resolve this hold')
    hold.active = False
    hold.resolved_by = actor.subject
    hold.resolution = body.resolution
    hold.evidence_document_id = body.evidence_document_id
    case.version += 1
    audit(db, case.institution_id, actor.subject, 'RELEASE_HOLD_RESOLVED', case.id,
          {'hold_id': hold.id, 'resolution': body.resolution, 'evidence_document_id': body.evidence_document_id}, request_id)
    return case_detail(db, case)


def gate_approval(db, case):
    from sentinel.integrations import require_no_blockers
    require_no_blockers(db, db.get(Deposit, case.deposit_id))
    if case.policy_revision != POLICY_REVISION:
        raise HTTPException(409, 'Release policy changed; request fresh registration and clearance scrutiny')
    blocking = blockers(db, case)
    if blocking:
        raise HTTPException(409, 'Release blocked: ' + '; '.join(blocking))
    if validate_case_evidence(db, case) != case.submitted_document_hash:
        raise HTTPException(409, 'Submitted evidence changed; fresh scrutiny required')
    deposit = db.get(Deposit, case.deposit_id)
    if deposit.workflow != 'ACCEPTED' or deposit.lifecycle_status == 'REPLACED':
        raise HTTPException(409, 'Deposit is unavailable for release')
    if current_evaluation(db, deposit).result['outcome'] == 'FAIL':
        raise HTTPException(409, 'Substantive blockers remain')


def approve_case(db, actor, case_id, body, request_id):
    case = get_case(db, actor, case_id, lock=True, roles=['APPROVER'])
    require_decision_assurance(actor)
    case_version(case, body.expected_version)
    gate_approval(db, case)
    if case.state != 'APPROVAL_REVIEW':
        raise HTTPException(409, 'Case not awaiting independent approval')
    decision_actors = set(db.scalars(select(ClearanceDecision.actor).where(ClearanceDecision.case_id == case.id)))
    registration_actors = set(db.scalars(select(ReviewDecision.actor).where(
        ReviewDecision.deposit_id == case.deposit_id)))
    if actor.subject in {case.maker, db.get(Deposit, case.deposit_id).maker, *decision_actors, *registration_actors}:
        raise HTTPException(403, 'Final approver must be independent of maker and prior decisions')
    case.state = 'APPROVED_SYNTHETIC'
    case.approver = actor.subject
    case.regulatory_basis = body.regulatory_basis
    case.version += 1
    audit(db, case.institution_id, actor.subject, 'RELEASE_APPROVED_SYNTHETIC', case.id,
          {'regulatory_basis': body.regulatory_basis, 'no_financial_authority': True}, request_id)
    return case_detail(db, case)


def issue_case(db, actor, case_id, body, request_id):
    case = get_case(db, actor, case_id, lock=True, roles=['ISSUER'])
    require_decision_assurance(actor)
    case_version(case, body.expected_version, ['APPROVED_SYNTHETIC'])
    gate_approval(db, case)
    deposit = db.get(Deposit, case.deposit_id)
    if deposit.deposit_type == 'OTHER_LEGACY':
        raise HTTPException(409, 'Unknown legacy issuance branch requires policy-owner definition')
    bureau = 'APPROVAL_BUREAU' if deposit.deposit_type in ('FDR', 'RPGF') else 'COUNCIL'
    if not actor.allows('ISSUER', 'BUREAU', bureau):
        raise HTTPException(403, 'Type-specific issuer scope required')
    prior_actors = set(db.scalars(select(ClearanceDecision.actor).where(ClearanceDecision.case_id == case.id)))
    if actor.subject in {case.maker, deposit.maker, case.approver, *prior_actors}:
        raise HTTPException(403, 'Independent issuer required')
    output_kind = 'NOC' if bureau == 'APPROVAL_BUREAU' else 'SANCTION ORDER'
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((45, 65), 'SYNTHETIC DEMONSTRATION ONLY', fontsize=22, color=(0.7, 0.1, 0.1))
    page.insert_text((45, 110), f'FDR Sentinel - Sample {output_kind}', fontsize=17)
    page.insert_textbox(pymupdf.Rect(45, 150, 550, 500),
                        f'NOT A VALID {output_kind}. NO PAYMENT OR BANK AUTHORITY.\n\n'
                        f'Case: {case.id}\nDeposit: {case.deposit_id}\n'
                        f'Deposit type: {deposit.deposit_type}\nDeclared INR: {Decimal(deposit.amount_paise) / 100:.2f}\n'
                        f'Approval actor: {case.approver}\nIssuance actor: {actor.subject}\n\n'
                        'External institutions: sandbox only, no official bank/AICTE verification.\n'
                        'Regulatory policy: provisional APH 2024-27 fixture.\n'
                        'This output demonstrates a controlled workflow only.\nNo settlement has occurred.', fontsize=12)
    data = pdf.tobytes()
    pdf.close()
    document_id = uid()
    key = f'generated/{case.institution_id}/{document_id}.pdf'
    try:
        put_original(key, data)
    except Exception:
        raise HTTPException(503, 'Private output storage unavailable') from None
    db.add(Document(id=document_id, deposit_id=deposit.id, institution_id=deposit.institution_id,
                    release_case_id=case.id, category='SYNTHETIC_OUTPUT', object_key=key,
                    sha256=hashlib.sha256(data).hexdigest(), size=len(data), status='READY',
                    scan_result='SYSTEM_GENERATED_SYNTHETIC_PDF', uploader=actor.subject))
    case.output_document_id = document_id
    case.issuer = actor.subject
    case.state = 'ISSUED_SYNTHETIC'
    case.version += 1
    # Do not set RELEASED: issuing a synthetic workflow result is not bank settlement.
    audit(db, case.institution_id, actor.subject, 'SYNTHETIC_' + output_kind.replace(' ', '_') + '_ISSUED', case.id,
          {'document_id': document_id, 'no_payment': True}, request_id)
    return case_detail(db, case)


def request_replacement(db, actor, body, request_id):
    deposits = [get_deposit(db, actor, i, lock=True, roles=['MAKER'])
                for i in sorted([body.old_deposit_id, body.new_deposit_id])]
    old = next(d for d in deposits if d.id == body.old_deposit_id)
    new = next(d for d in deposits if d.id == body.new_deposit_id)
    check_version(old, body.expected_old_version, ['ACCEPTED'])
    if (old.id == new.id or old.institution_id != new.institution_id or old.obligation_id != new.obligation_id
            or new.workflow != 'ACCEPTED' or old.lifecycle_status == 'REPLACED'
            or new.lifecycle_status == 'REPLACED'):
        raise HTTPException(409, 'Distinct accepted records under the same obligation required')
    if db.scalar(select(ReleaseCase.id).where(ReleaseCase.deposit_id.in_([old.id, new.id]))):
        raise HTTPException(409, 'Release case prevents replacement')
    document = db.get(Document, body.evidence_document_id)
    if not document or document.deposit_id != new.id or document.status != 'READY':
        raise HTTPException(409, 'READY replacement evidence from the new record required')
    record = Replacement(old_deposit_id=old.id, new_deposit_id=new.id, institution_id=old.institution_id,
                         kind=body.kind, rationale=body.rationale, evidence_document_id=document.id,
                         maker=actor.subject)
    db.add(record)
    db.flush()
    old.version += 1
    audit(db, old.institution_id, actor.subject, 'REPLACEMENT_REQUESTED', old.id,
          {'relationship_id': record.id, 'new_deposit_id': new.id, 'kind': body.kind}, request_id)
    return {'id': record.id, 'state': record.state, 'version': record.version}


def approve_replacement(db, actor, relationship_id, body, request_id):
    record = db.get(Replacement, relationship_id)
    if not record:
        raise HTTPException(404, 'Resource not found')
    for deposit_id in sorted([record.old_deposit_id, record.new_deposit_id]):
        get_deposit(db, actor, deposit_id, lock=True, roles=['REVIEWER'])
    record = db.scalar(select(Replacement).where(Replacement.id == relationship_id).with_for_update()
                       .execution_options(populate_existing=True))
    if record.version != body.expected_version or record.state != 'REQUESTED':
        raise HTTPException(409, 'Stale replacement request')
    old, new = db.get(Deposit, record.old_deposit_id), db.get(Deposit, record.new_deposit_id)
    if actor.subject in {record.maker, old.maker, new.maker}:
        raise HTTPException(403, 'Maker cannot authorize replacement')
    if db.scalar(select(ReleaseCase.id).where(ReleaseCase.deposit_id.in_([old.id, new.id]))):
        raise HTTPException(409, 'Release case prevents replacement')
    # Require strictly forward issue/deposit time to prevent replacement cycles.
    old_date, new_date = old.issue_date or old.deposited_on, new.issue_date or new.deposited_on
    if not old_date or not new_date or new_date <= old_date or new.amount_paise < old.amount_paise:
        raise HTTPException(409, 'Replacement must be later and preserve required principal; exceptions need review')
    record.state = 'AUTHORIZED'
    record.checker = actor.subject
    record.version += 1
    old.lifecycle_status = 'REPLACED'
    old.version += 1
    new.version += 1
    audit(db, old.institution_id, actor.subject, 'REPLACEMENT_AUTHORIZED', old.id,
          {'relationship_id': record.id, 'new_deposit_id': new.id, 'policy_basis': body.policy_basis}, request_id)
    return {'id': record.id, 'state': record.state, 'version': record.version}


def run_maturity(db, as_of, institution_ids=None, actor='scheduler', request_id='scheduled'):
    query = select(Deposit).where(Deposit.maturity_date.is_not(None), Deposit.lifecycle_status != 'REPLACED')
    if institution_ids is not None:
        query = query.where(Deposit.institution_id.in_(institution_ids))
    created = 0
    for deposit in db.scalars(query.with_for_update(skip_locked=True)):
        days = (deposit.maturity_date - as_of).days
        thresholds = sorted(set(t for t in settings().maturity_thresholds if t > 0))
        if not thresholds:
            raise RuntimeError('At least one positive maturity reminder threshold is required')
        status = 'MATURED' if days <= 0 else 'APPROACHING_MATURITY' if days <= max(thresholds) else 'ACTIVE'
        if deposit.lifecycle_status != status:
            deposit.lifecycle_status = status
            deposit.version += 1
            audit(db, deposit.institution_id, actor, 'MATURITY_STATE_UPDATED', deposit.id,
                  {'as_of': as_of.isoformat(), 'lifecycle_status': status,
                   'never_automatic_release': True}, request_id)
        threshold = 0 if days <= 0 else next((t for t in thresholds if days <= t), None)
        if threshold is not None:
            result = db.execute(insert(Notification).values(
                id=uid(), institution_id=deposit.institution_id, deposit_id=deposit.id,
                dedupe_key=f'{deposit.id}:{deposit.maturity_date}:{threshold}', recipient=deposit.maker,
                kind='MATURITY_IN_APP', detail={'days_remaining': days, 'threshold': threshold,
                                              'as_of': as_of.isoformat(), 'delivery': 'PERSISTED_IN_APP',
                                              'basis': 'CONFIGURABLE_PRODUCT_POLICY_NOT_STATUTORY'},
            ).on_conflict_do_nothing().returning(Notification.id)).scalar_one_or_none()
            if result:
                from sentinel.delivery import ensure_delivery
                ensure_delivery(db, result)
                created += 1
                audit(db, deposit.institution_id, actor, 'MATURITY_ALERT_CREATED', deposit.id,
                      {'notification_id': result, 'threshold': threshold}, request_id)
    return {'notifications_created': created, 'as_of': as_of.isoformat(), 'no_automatic_release': True}
