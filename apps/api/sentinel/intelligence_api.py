from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import Field, FiniteFloat
from sqlalchemy import select
from sqlalchemy.orm import Session

from sentinel import intelligence
from sentinel.adapters import MockBankAdapter
from sentinel.auth import Actor, authenticate
from sentinel.db import get_db
from sentinel.models import Discrepancy, Document, ExtractionCorrection, Outbox, VerificationAttestation
from sentinel.schemas import StrictModel, VersionCommand
from sentinel.services import check_version, current_evaluation, get_deposit
from sentinel.transactions import audit, mutate

router = APIRouter(prefix='/api/v1')


class CorrectionProposal(StrictModel):
    field: Literal['amount_paise', 'issue_date', 'maturity_date', 'institution_external_id']
    value: str = Field(min_length=1, max_length=120)
    page: int = Field(ge=1, le=30)
    bounds: tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]
    quote: str = Field(min_length=1, max_length=240)
    reason: str = Field(min_length=10, max_length=2000)


class CorrectionDecision(StrictModel):
    decision: Literal['CONFIRMED', 'REJECTED']
    reason: str = Field(min_length=10, max_length=2000)


class DiscrepancyResolution(StrictModel):
    reason: str = Field(min_length=10, max_length=2000)
    evidence_document_id: str


class SimulationIn(VersionCommand):
    scenario: Literal['MATCH', 'AMOUNT_MISMATCH', 'UNAVAILABLE']


def scoped_document(db, actor, document_id, roles=None, lock=False):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, 'Resource not found')
    deposit = get_deposit(db, actor, document.deposit_id, lock=lock, roles=roles)
    return document, deposit


@router.post('/documents/{document_id}/corrections')
def propose(document_id: str, body: CorrectionProposal, request: Request, actor: Actor = Depends(authenticate),
            db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    scoped_document(db, actor, document_id, ['MAKER', 'REVIEWER'])
    def action():
        document, deposit = scoped_document(db, actor, document_id, ['MAKER', 'REVIEWER'], lock=True)
        return intelligence.propose_correction(db, actor, document, deposit, body, request.state.request_id)
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)


@router.get('/deposits/{deposit_id}/intelligence')
def intelligence_detail(deposit_id: str, actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    get_deposit(db, actor, deposit_id)
    document_ids = select(Document.id).where(Document.deposit_id == deposit_id)
    return {'corrections': [{'id': c.id, 'document_id': c.document_id, 'field': c.field, 'value': c.value,
                             'page': c.page, 'bounds': c.bounds, 'quote': c.quote, 'reason': c.reason,
                             'status': c.status, 'maker': c.maker, 'checker': c.checker}
                            for c in db.scalars(select(ExtractionCorrection).where(
                                ExtractionCorrection.document_id.in_(document_ids)).limit(100))],
            'discrepancies': [{'id': d.id, 'status': d.status, 'finding': d.finding,
                               'adjudicator': d.adjudicator, 'resolution': d.resolution}
                              for d in db.scalars(select(Discrepancy).where(
                                  Discrepancy.deposit_id == deposit_id).limit(100))],
            'attestations': [{'id': a.id, 'source': a.source, 'outcome': a.outcome,
                              'payload': a.payload, 'signature': a.signature,
                              'signature_type': 'LOCAL_DEMO_HMAC_NOT_BANK_PKI'}
                             for a in db.scalars(select(VerificationAttestation).where(
                                 VerificationAttestation.deposit_id == deposit_id).limit(100))]}


@router.post('/corrections/{correction_id}/decision')
def decide(correction_id: str, body: CorrectionDecision, request: Request, actor: Actor = Depends(authenticate),
           db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    correction = db.get(ExtractionCorrection, correction_id)
    if not correction:
        raise HTTPException(404, 'Resource not found')
    scoped_document(db, actor, correction.document_id, ['REVIEWER'])
    def action():
        document, deposit = scoped_document(db, actor, correction.document_id, ['REVIEWER'], lock=True)
        current = db.scalar(select(ExtractionCorrection).where(ExtractionCorrection.id == correction_id)
                            .execution_options(populate_existing=True))
        return intelligence.decide_correction(db, actor, current, document, deposit, body, request.state.request_id)
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)


@router.post('/discrepancies/{discrepancy_id}/resolve')
def resolve(discrepancy_id: str, body: DiscrepancyResolution, request: Request,
            actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
            idempotency_key: str | None = Header(None)):
    discrepancy = db.get(Discrepancy, discrepancy_id)
    if not discrepancy:
        raise HTTPException(404, 'Resource not found')
    get_deposit(db, actor, discrepancy.deposit_id, roles=['REVIEWER'])
    def action():
        deposit = get_deposit(db, actor, discrepancy.deposit_id, roles=['REVIEWER'], lock=True)
        current = db.scalar(select(Discrepancy).where(Discrepancy.id == discrepancy_id)
                            .execution_options(populate_existing=True))
        document = db.get(Document, body.evidence_document_id)
        if not document:
            raise HTTPException(404, 'Resource not found')
        return intelligence.resolve_discrepancy(db, actor, deposit, current, body,
                                              current_evaluation(db, deposit), document, request.state.request_id)
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)


@router.post('/deposits/{deposit_id}/verify-simulated')
def verify(deposit_id: str, body: SimulationIn, request: Request, actor: Actor = Depends(authenticate),
           db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    get_deposit(db, actor, deposit_id, roles=['REVIEWER'])
    def action():
        deposit = get_deposit(db, actor, deposit_id, lock=True, roles=['REVIEWER'])
        check_version(deposit, body.expected_version)
        try:
            result = MockBankAdapter().request_verification(deposit.id, {
                'amount_paise': deposit.amount_paise,
                'maturity_date': deposit.maturity_date.isoformat() if deposit.maturity_date else None,
                'reference_last4': deposit.reference_last4,
            }, idempotency_key, scenario=body.scenario)
        except RuntimeError:
            raise HTTPException(503, 'Local simulated adapter unavailable; run bootstrap') from None
        record = VerificationAttestation(deposit_id=deposit.id, source='SIMULATED_BANK_FIXTURE',
                                         outcome=result['outcome'], payload=result['payload'],
                                         signature=result['signature'], requested_by=actor.subject)
        db.add(record)
        db.flush()
        deposit.version += 1
        audit(db, deposit.institution_id, actor.subject, 'SIMULATED_BANK_SCENARIO_RECORDED', deposit.id,
              {'attestation_id': record.id, 'outcome': record.outcome,
               'verification_status_unchanged': deposit.verification_status}, request.state.request_id)
        return {'id': record.id, **result, 'verification_status': deposit.verification_status}
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)


@router.post('/documents/{document_id}/retry')
def retry(document_id: str, body: VersionCommand, request: Request, actor: Actor = Depends(authenticate),
          db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    scoped_document(db, actor, document_id, ['REVIEWER'])
    def action():
        document, deposit = scoped_document(db, actor, document_id, ['REVIEWER'], lock=True)
        check_version(deposit, body.expected_version)
        if document.status != 'FAILED':
            raise HTTPException(409, 'Only failed processing can be retried')
        event = db.scalar(select(Outbox).where(Outbox.aggregate_id == document.id).with_for_update())
        event.processing_attempts = 0
        event.dead_lettered_at = None
        event.published_at = None
        event.completed_at = None
        document.status = 'QUARANTINED'
        document.scan_result = None
        deposit.version += 1
        audit(db, deposit.institution_id, actor.subject, 'DOCUMENT_RETRY_REQUESTED', deposit.id,
              {'document_id': document.id, 'event_id': event.id}, request.state.request_id)
        return {'document_id': document.id, 'status': document.status, 'event_id': event.id}
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'), action)
