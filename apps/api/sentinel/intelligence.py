"""Evidence corrections and discrepancy adjudication; all changes require scoped humans."""
from datetime import date
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select

from sentinel.compliance import digest
from sentinel.models import Discrepancy, ExtractionCorrection, now
from sentinel.transactions import audit


def effective_documents(db, documents):
    output = []
    for document in documents:
        evidence = list(document.evidence)
        corrections = db.scalars(select(ExtractionCorrection).where(
            ExtractionCorrection.document_id == document.id, ExtractionCorrection.status == 'CONFIRMED'
        ).order_by(ExtractionCorrection.decided_at, ExtractionCorrection.id)).all()
        for correction in corrections:
            evidence = [e for e in evidence if e['field'] != correction.field]
            evidence.append({'field': correction.field,
                             'value': int(correction.value) if correction.field == 'amount_paise' else correction.value,
                             'page': correction.page, 'bounds': correction.bounds, 'quote': correction.quote,
                             'method': 'OFFICER_CONFIRMED_TRANSCRIPTION', 'correction_id': correction.id,
                             'actor': correction.checker, 'confidence': None, 'algorithm': 'human-provenance-v1'})
        output.append(SimpleNamespace(id=document.id, sha256=document.sha256, evidence=evidence,
                                      status=document.status, category=document.category))
    return output


def finding_key(finding):
    return digest({'code': finding['code'], 'field': finding.get('field')})


def register_discrepancies(db, deposit, evaluation):
    for finding in evaluation.result['findings']:
        if finding['severity'] != 'FAIL':
            continue
        key = finding_key(finding)
        existing = db.scalar(select(Discrepancy).where(Discrepancy.deposit_id == deposit.id,
                                                      Discrepancy.finding_key == key))
        if existing:
            existing.status = 'OPEN'
            existing.finding = finding
            existing.evaluation_id = evaluation.id
            existing.adjudicator = None
            existing.resolution = None
        else:
            db.add(Discrepancy(deposit_id=deposit.id, evaluation_id=evaluation.id,
                               finding_key=key, finding=finding))


def propose_correction(db, actor, document, deposit, body, request_id):
    if document.status != 'READY' or not document.active or document.release_case_id:
        raise HTTPException(409, 'Active scanned registration evidence required')
    if deposit.workflow not in ('DRAFT', 'PENDING_SCRUTINY'):
        raise HTTPException(409, 'Accepted records cannot silently change evidence interpretation')
    page_sizes = document.processing_metadata.get('page_sizes', [])
    if not 1 <= body.page <= len(page_sizes):
        raise HTTPException(422, 'Page is unavailable; current processing metadata required')
    width, height = page_sizes[body.page - 1]
    x0, y0, x1, y1 = body.bounds
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise HTTPException(422, 'Evidence bounds must lie inside the selected page')
    if body.field == 'amount_paise':
        if not body.value.isdigit() or not 0 < int(body.value) <= 1_000_000_000_000:
            raise HTTPException(422, 'Amount must be positive integer paise')
    elif body.field in ('issue_date', 'maturity_date'):
        try:
            date.fromisoformat(body.value)
        except ValueError:
            raise HTTPException(422, 'Date must be ISO YYYY-MM-DD') from None
    record = ExtractionCorrection(**body.model_dump(), document_id=document.id, maker=actor.subject)
    db.add(record)
    db.flush()
    deposit.version += 1
    audit(db, deposit.institution_id, actor.subject, 'EXTRACTION_CORRECTION_PROPOSED', deposit.id,
          {'correction_id': record.id, 'document_id': document.id, 'field': record.field,
           'page': record.page, 'bounds': record.bounds, 'reason': record.reason}, request_id)
    return {'id': record.id, 'status': record.status, 'authority': 'PROPOSED_NOT_CONFIRMED'}


def decide_correction(db, actor, correction, document, deposit, body, request_id):
    if correction.status != 'PROPOSED' or deposit.workflow == 'ACCEPTED':
        raise HTTPException(409, 'Pending correction on unaccepted record required')
    if actor.subject in {correction.maker, deposit.maker}:
        raise HTTPException(403, 'Correction confirmation requires an independent reviewer')
    correction.status = body.decision
    correction.checker = actor.subject
    correction.decided_at = now()
    deposit.version += 1
    if body.decision == 'CONFIRMED':
        deposit.input_revision += 1
    audit(db, deposit.institution_id, actor.subject, 'EXTRACTION_CORRECTION_' + body.decision, deposit.id,
          {'correction_id': correction.id, 'document_id': document.id, 'reason': body.reason,
           'input_revision': deposit.input_revision}, request_id)
    return {'id': correction.id, 'status': correction.status, 'input_revision': deposit.input_revision}


def resolve_discrepancy(db, actor, deposit, discrepancy, body, evaluation, document, request_id):
    if discrepancy.status != 'OPEN':
        raise HTTPException(409, 'Discrepancy already resolved')
    if any(f['severity'] == 'FAIL' and finding_key(f) == discrepancy.finding_key
           for f in evaluation.result['findings']):
        raise HTTPException(409, 'Current evaluation still contains this blocker; correct and reevaluate first')
    if actor.subject == deposit.maker:
        raise HTTPException(403, 'Maker cannot resolve their own discrepancy')
    if document.deposit_id != deposit.id or document.status != 'READY' or not document.active:
        raise HTTPException(409, 'Active READY resolution evidence required')
    discrepancy.status = 'RESOLVED'
    discrepancy.adjudicator = actor.subject
    discrepancy.resolution = body.reason
    discrepancy.evidence_document_id = document.id
    deposit.version += 1
    audit(db, deposit.institution_id, actor.subject, 'DISCREPANCY_RESOLVED', deposit.id,
          {'discrepancy_id': discrepancy.id, 'evaluation_id': evaluation.id,
           'evidence_document_id': document.id, 'reason': body.reason}, request_id)
    return {'id': discrepancy.id, 'status': discrepancy.status}
