import hashlib
import hmac

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from sentinel.auth import Actor, require_scope
from sentinel.compliance import POLICY_REVISION, digest, document_set_hash, evaluate, required_amount
from sentinel.config import settings
from sentinel.intelligence import effective_documents, register_discrepancies
from sentinel.models import (
    Deposit,
    Discrepancy,
    Document,
    Evaluation,
    Institution,
    Obligation,
    Outbox,
    ReleaseCase,
    ReviewDecision,
    RoleBinding,
    uid,
)
from sentinel.schemas import DepositOut, DocumentOut, EvaluationOut, InstitutionOut, ObligationOut
from sentinel.storage import put_original
from sentinel.transactions import audit


def dto(model, schema):
    return schema.model_validate(model, from_attributes=True).model_dump(mode='json')


def get_deposit(db: Session, actor: Actor, deposit_id: str, lock=False, roles=None):
    query = select(Deposit).where(Deposit.id == deposit_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    deposit = db.scalar(query)
    if not deposit:
        raise HTTPException(404, 'Resource not found')
    if not roles and deposit.institution_id not in actor.institution_ids():
        if not db.scalar(select(ReleaseCase.id).where(ReleaseCase.deposit_id == deposit.id,
                                                      ReleaseCase.id.in_(actor.case_ids()))):
            raise HTTPException(404, 'Resource not found')
    else:
        require_scope(actor, deposit.institution_id, roles)
    return deposit


def check_version(deposit: Deposit, expected: int, states=None):
    if deposit.version != expected:
        raise HTTPException(409, 'Stale version; reload and retry')
    if states and deposit.workflow not in states:
        raise HTTPException(409, f'Operation unavailable in {deposit.workflow}')


def onboarding(db, actor, body, request_id):
    # A reviewer may also have a legitimate maker scope elsewhere; self-onboarding does
    # not grant them reviewer authority on the newly created institution.
    institution = Institution(**body.model_dump(exclude={'context'}), context=body.context.model_dump(),
                              owner=actor.subject)
    db.add(institution)
    db.flush()
    db.add(RoleBinding(subject=actor.subject, role='MAKER', scope_type='INSTITUTION', scope_id=institution.id))
    audit(db, institution.id, actor.subject, 'INSTITUTION_DECLARED', institution.id,
          {'registry_status': institution.registry_status}, request_id)
    return dto(institution, InstitutionOut)


def create_obligation(db, actor, body, request_id):
    require_scope(actor, body.institution_id, ['MAKER'])
    institution = db.get(Institution, body.institution_id)
    record = Obligation(**body.model_dump(), context=dict(institution.context), policy_revision=POLICY_REVISION,
                        required_amount_paise=required_amount(institution.context, body.regulatory_event))
    db.add(record)
    db.flush()
    audit(db, record.institution_id, actor.subject, 'OBLIGATION_DECLARED', record.id,
          {'regulatory_event': record.regulatory_event, 'policy_revision': POLICY_REVISION}, request_id)
    return dto(record, ObligationOut)


def create_deposit(db, actor, body, request_id):
    obligation = db.get(Obligation, body.obligation_id)
    if not obligation:
        raise HTTPException(404, 'Resource not found')
    require_scope(actor, obligation.institution_id, ['MAKER'])
    reference = body.reference.upper()
    config = settings()
    record = Deposit(**body.model_dump(exclude={'reference'}), institution_id=obligation.institution_id,
                     reference_last4=reference[-4:], hmac_version=config.reference_hmac_version,
                     reference_digest=hmac.new(config.reference_hmac_key.encode(), reference.encode(),
                                               hashlib.sha256).hexdigest(), maker=actor.subject)
    db.add(record)
    db.flush()
    audit(db, record.institution_id, actor.subject, 'DEPOSIT_RECORDED', record.id,
          {'deposit_type': record.deposit_type, 'version': record.version}, request_id)
    return dto(record, DepositOut)


def documents_for(db, deposit, active_only=True):
    query = select(Document).where(Document.deposit_id == deposit.id, Document.release_case_id.is_(None))
    if active_only:
        query = query.where(Document.active.is_(True))
    return db.scalars(query.order_by(Document.id)).all()


def detail(db, actor, deposit_id):
    deposit = get_deposit(db, actor, deposit_id)
    result = dto(deposit, DepositOut)
    result['documents'] = [dto(d, DocumentOut) for d in documents_for(db, deposit, active_only=False)]
    result['evaluations'] = [dto(e, EvaluationOut) for e in db.scalars(select(Evaluation).where(
        Evaluation.deposit_id == deposit.id).order_by(Evaluation.evaluated_at.desc()).limit(20))]
    result['decisions'] = [{'actor': r.actor, 'decision': r.decision, 'reason': r.reason,
                            'created_at': r.created_at.isoformat()} for r in db.scalars(
        select(ReviewDecision).where(ReviewDecision.deposit_id == deposit.id))]
    return result


def upload(db, actor, deposit_id, data, category, request_id, supersedes_id=None):
    deposit = get_deposit(db, actor, deposit_id, lock=True, roles=['MAKER'])
    if deposit.workflow != 'DRAFT':
        raise HTTPException(409, 'Return to draft before adding evidence')
    if len(documents_for(db, deposit, active_only=False)) >= 20:
        raise HTTPException(409, 'Document limit reached')
    previous = None
    if supersedes_id:
        previous = db.get(Document, supersedes_id)
        if not previous or previous.deposit_id != deposit.id or not previous.active:
            raise HTTPException(409, 'Superseded document must be active in this deposit')
        if previous.category != category:
            raise HTTPException(409, 'Superseding document category must match')
    object_id = uid()
    key = f'originals/{deposit.institution_id}/{object_id}.pdf'
    try:
        put_original(key, data)
    except Exception:
        raise HTTPException(503, 'Private document storage unavailable') from None
    document = Document(id=object_id, deposit_id=deposit.id, institution_id=deposit.institution_id,
                        category=category, object_key=key, sha256=hashlib.sha256(data).hexdigest(),
                        size=len(data), uploader=actor.subject, supersedes_id=supersedes_id)
    if previous:
        previous.active = False
    db.add(document)
    db.flush()
    db.add(Outbox(aggregate_id=document.id))
    deposit.input_revision += 1
    deposit.version += 1
    audit(db, deposit.institution_id, actor.subject, 'DOCUMENT_QUARANTINED', deposit.id,
          {'document_id': document.id, 'sha256': document.sha256, 'input_revision': deposit.input_revision},
          request_id)
    return dto(document, DocumentOut)


def correct(db, actor, deposit_id, body, request_id):
    deposit = get_deposit(db, actor, deposit_id, lock=True, roles=['MAKER'])
    check_version(deposit, body.expected_version, ['DRAFT'])
    if deposit.deposit_type == 'FDR' and (body.issue_date is None or body.maturity_date is None):
        raise HTTPException(422, 'FDR correction requires issue and maturity dates')
    if deposit.deposit_type in ('RTGS', 'ONLINE') and not body.deposited_on:
        raise HTTPException(422, 'Deposit date required')
    for field, value in body.model_dump(exclude={'expected_version'}).items():
        setattr(deposit, field, value)
    deposit.input_revision += 1
    deposit.version += 1
    audit(db, deposit.institution_id, actor.subject, 'DECLARATION_CORRECTED', deposit.id,
          {'input_revision': deposit.input_revision, 'version': deposit.version}, request_id)
    return dto(deposit, DepositOut)


def build_inputs(db, deposit):
    obligation = db.get(Obligation, deposit.obligation_id)
    institution = db.get(Institution, deposit.institution_id)
    return jsonable_encoder({'amount_paise': deposit.amount_paise, 'issue_date': deposit.issue_date,
                             'maturity_date': deposit.maturity_date, 'deposited_on': deposit.deposited_on,
                             'deposit_type': deposit.deposit_type, 'context': obligation.context,
                             'regulatory_event': obligation.regulatory_event,
                             'institution_external_id': institution.external_id})


def run_evaluation(db, actor, deposit_id, body, request_id):
    deposit = get_deposit(db, actor, deposit_id, lock=True, roles=['MAKER', 'REVIEWER'])
    check_version(deposit, body.expected_version, ['DRAFT', 'PENDING_SCRUTINY'])
    documents = documents_for(db, deposit)
    if not any(d.status == 'READY' and d.category == 'DEPOSIT_PROOF' for d in documents):
        raise HTTPException(409, 'Incomplete intake: scanned deposit proof required')
    if any(d.status != 'READY' for d in documents):
        raise HTTPException(409, 'All evidence must pass scanning before evaluation')
    documents = effective_documents(db, documents)
    inputs = build_inputs(db, deposit)
    evaluation = Evaluation(deposit_id=deposit.id, input_revision=deposit.input_revision,
                            policy_revision=POLICY_REVISION, document_set_hash=document_set_hash(documents),
                            inputs=inputs, input_hash=digest(inputs), result=evaluate(inputs, documents))
    db.add(evaluation)
    db.flush()
    register_discrepancies(db, deposit, evaluation)
    deposit.version += 1
    audit(db, deposit.institution_id, actor.subject, 'COMPLIANCE_EVALUATED', deposit.id,
          {'evaluation_id': evaluation.id, 'outcome': evaluation.result['outcome'],
           'policy_revision': POLICY_REVISION}, request_id)
    return dto(evaluation, EvaluationOut)


def current_evaluation(db, deposit):
    evaluation = db.scalar(select(Evaluation).where(Evaluation.deposit_id == deposit.id).order_by(
        Evaluation.evaluated_at.desc()).limit(1))
    documents = effective_documents(db, documents_for(db, deposit))
    if not evaluation or (evaluation.input_revision, evaluation.policy_revision, evaluation.document_set_hash) != (
            deposit.input_revision, POLICY_REVISION, document_set_hash(documents)):
        raise HTTPException(409, 'Evaluation is missing or stale; reevaluate current evidence')
    return evaluation


def submit(db, actor, deposit_id, body, request_id):
    deposit = get_deposit(db, actor, deposit_id, lock=True, roles=['MAKER'])
    check_version(deposit, body.expected_version, ['DRAFT'])
    evaluation = current_evaluation(db, deposit)
    deposit.workflow = 'PENDING_SCRUTINY'
    deposit.version += 1
    audit(db, deposit.institution_id, actor.subject, 'SUBMITTED_FOR_SCRUTINY', deposit.id,
          {'outcome': evaluation.result['outcome'], 'version': deposit.version}, request_id)
    return dto(deposit, DepositOut)


def review(db, actor, deposit_id, body, request_id):
    deposit = get_deposit(db, actor, deposit_id, lock=True, roles=['REVIEWER'])
    check_version(deposit, body.expected_version, ['PENDING_SCRUTINY'])
    if deposit.maker == actor.subject:
        raise HTTPException(403, 'Maker cannot review their own deposit')
    evaluation = current_evaluation(db, deposit)
    if body.decision == 'ACCEPT_REGISTRATION':
        if evaluation.result['outcome'] == 'FAIL':
            raise HTTPException(409, 'Unresolved substantive blockers prevent acceptance')
        if not body.evidence_reviewed:
            raise HTTPException(409, 'Explicit human evidence review required')
        if db.scalar(select(Discrepancy.id).where(Discrepancy.deposit_id == deposit.id,
                                                Discrepancy.status == 'OPEN')):
            raise HTTPException(409, 'Officer must disposition all discrepancy records before acceptance')
        deposit.workflow = 'ACCEPTED'
        deposit.verification_status = 'MANUALLY_REVIEWED'
    else:
        deposit.workflow = 'DRAFT'
    db.add(ReviewDecision(deposit_id=deposit.id, actor=actor.subject, decision=body.decision,
                          reason=body.reason, evaluation_id=evaluation.id, version=deposit.version))
    deposit.version += 1
    audit(db, deposit.institution_id, actor.subject, body.decision, deposit.id,
          {'version': deposit.version, 'evaluation_id': evaluation.id, 'reason': body.reason}, request_id)
    return dto(deposit, DepositOut)
