import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pymupdf
import pytest
from conftest import create_deposit, evaluate_submit, latest, pdf_bytes, post, upload_and_process
from sqlalchemy import select

pytestmark = pytest.mark.integration


def test_realistic_digital_and_scanned_field_measurements(services_ready):
    from scripts.benchmark_extraction import benchmark
    result = benchmark()
    assert result['documents'] == 4 and result['expected_fields'] == 16
    assert result['precision'] == 1 and result['recall'] == 1, result
    assert next(c for c in result['cases'] if c['case'] == 'scanned')['ocr_pages'] == 1


def test_independent_evidence_correction_and_discrepancy_resolution(clients, monkeypatch):
    from sentinel.db import session_factory
    from sentinel.jobs import process_document
    from sentinel.models import Outbox
    maker, officer = clients(), clients('reviewer')
    deposit = create_deposit(maker)
    # Inject an extraction error while preserving the correct immutable original.
    from sentinel.extraction import extract_document
    def extraction_fault(data):
        evidence, metadata = extract_document(data, use_ai=False)
        for item in evidence:
            if item['field'] == 'amount_paise':
                item['value'] = 300000000
                item['method'] = 'FAULT_INJECTED_OCR_MISREAD_TEST'
        return evidence, metadata
    with monkeypatch.context() as fault:
        fault.setattr('sentinel.jobs.extract_document', extraction_fault)
        doc = upload_and_process(maker, deposit, amount=350000000)
    current = evaluate_submit(maker, deposit)
    registry = maker.get(f"/api/v1/deposits/{deposit['id']}/intelligence").json()
    mismatch = next(d for d in registry['discrepancies'] if d['finding']['code'] == 'DOCUMENT_MISMATCH')
    assert mismatch['finding']['evidence']['sha256'] == doc['sha256']
    assert post(officer, f"/discrepancies/{mismatch['id']}/resolve", {
        'reason': 'Attempt to waive still present mismatch', 'evidence_document_id': doc['id']}).status_code == 409
    # A human transcription is proposed against page bounds and independently confirmed.
    proposal = post(maker, f"/documents/{doc['id']}/corrections", {
        'field': 'amount_paise', 'value': '350000000', 'page': 1, 'bounds': [50, 130, 400, 180],
        'quote': 'Amount paise: 350000000',
        'reason': 'Synthetic original inspected; correction explicitly human asserted.'})
    assert proposal.status_code == 200, proposal.text
    correction_id = proposal.json()['id']
    assert post(maker, f'/corrections/{correction_id}/decision', {
        'decision': 'CONFIRMED', 'reason': 'Maker may not self-confirm'}).status_code == 403
    confirmed = post(officer, f'/corrections/{correction_id}/decision', {
        'decision': 'CONFIRMED', 'reason': 'Synthetic evidence region inspected; human transcription confirmed.'})
    assert confirmed.status_code == 200, confirmed.text
    current = latest(maker, deposit)
    stale = post(officer, f"/deposits/{deposit['id']}/review", {
        'expected_version': current['version'], 'decision': 'ACCEPT_REGISTRATION',
        'reason': 'Stale evaluation must prevent acceptance', 'evidence_reviewed': True})
    assert stale.status_code == 409
    evaluated = post(officer, f"/deposits/{deposit['id']}/evaluate", {'expected_version': current['version']})
    assert evaluated.status_code == 200 and evaluated.json()['result']['outcome'] != 'FAIL'
    resolved = post(officer, f"/discrepancies/{mismatch['id']}/resolve", {
        'reason': 'Independent human correction verified; fresh evaluation has no mismatch.',
        'evidence_document_id': doc['id']})
    assert resolved.status_code == 200
    current = latest(maker, deposit)
    assert post(officer, f"/deposits/{deposit['id']}/review", {
        'expected_version': current['version'], 'decision': 'ACCEPT_REGISTRATION',
        'reason': 'Synthetic registration accepted with independent evidence review.', 'evidence_reviewed': True}).status_code == 200
    # Processing cannot duplicate even when redelivered concurrently.
    with session_factory()() as db:
        event_id = db.scalar(select(Outbox.id).where(Outbox.aggregate_id == doc['id']))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: process_document.run(event_id), range(2)))
    assert results == ['ALREADY_COMPLETED', 'ALREADY_COMPLETED']


def test_simulated_adapter_signature_and_source_distinction(clients):
    from sentinel.config import settings
    maker, officer = clients(), clients('reviewer')
    deposit = create_deposit(maker)
    key = str(uuid4())
    body = {'expected_version': deposit['version'], 'scenario': 'AMOUNT_MISMATCH'}
    result = post(officer, f"/deposits/{deposit['id']}/verify-simulated", body, key)
    assert result.status_code == 200, result.text
    data = result.json()
    expected = hmac.new(settings().mock_attestation_key.encode(),
                        json.dumps(data['payload'], sort_keys=True, separators=(',', ':')).encode(),
                        hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, data['signature'])
    assert data['outcome'] == 'SIMULATED_AMOUNT_MISMATCH'
    assert data['payload']['authenticity'] == 'SIMULATED_NOT_BANK_CONFIRMED'
    assert post(officer, f"/deposits/{deposit['id']}/verify-simulated", body, key).json() == data
    assert latest(maker, deposit)['verification_status'] == 'INSTITUTION_DECLARED'
    assert post(maker, f"/deposits/{deposit['id']}/verify-simulated", body).status_code == 403


def test_real_private_store_and_scoped_preview(clients):
    from sentinel.config import settings
    from sentinel.db import session_factory
    from sentinel.models import Document
    maker = clients()
    deposit = create_deposit(maker)
    doc = upload_and_process(maker, deposit)
    response = maker.get(f"/api/v1/documents/{doc['id']}/preview/1")
    assert response.status_code == 200 and response.content.startswith(b'\x89PNG')
    assert clients('other-institution').get(f"/api/v1/documents/{doc['id']}/preview/1").status_code == 404
    with session_factory()() as db:
        key = db.get(Document, doc['id']).object_key
    config = settings()
    unsigned = httpx.get(f'http://{config.s3_endpoint}/{config.s3_bucket}/{key}', timeout=10)
    assert unsigned.status_code in (401, 403)


def test_dead_letter_and_officer_retry(clients, monkeypatch):
    from sentinel.db import session_factory
    from sentinel.jobs import process_document
    from sentinel.models import Outbox
    maker = clients()
    deposit = create_deposit(maker)
    doc = maker.post(f"/api/v1/deposits/{deposit['id']}/documents", files={
        'file': ('test.pdf', pdf_bytes(), 'application/pdf')}, headers={'Idempotency-Key': str(uuid4())}).json()
    with session_factory()() as db:
        event_id = db.scalar(select(Outbox.id).where(Outbox.aggregate_id == doc['id']))
    def outage(_):
        raise ConnectionError('Injected scanner outage')
    monkeypatch.setattr('sentinel.jobs.scan_bytes', outage)
    for attempt in range(5):
        if attempt < 4:
            with pytest.raises(Exception):
                process_document.run(event_id)
        else:
            assert process_document.run(event_id) == 'DEAD_LETTER'
    current = latest(maker, deposit)
    assert current['documents'][0]['status'] == 'FAILED'
    assert 'DEAD_LETTER' in current['documents'][0]['scan_result']
    assert maker.get(f"/api/v1/documents/{doc['id']}/content").status_code == 409
    retried = post(clients('reviewer'), f"/documents/{doc['id']}/retry", {'expected_version': current['version']})
    assert retried.status_code == 200
    assert latest(maker, deposit)['documents'][0]['status'] == 'QUARANTINED'


def test_malformed_and_page_limit_fail_closed(clients):
    from sentinel.extraction import extract_document
    with pytest.raises(ValueError):
        extract_document(b'%PDF-broken', use_ai=False)
    pdf = pymupdf.open()
    for _ in range(31):
        pdf.new_page()
    data = pdf.tobytes()
    pdf.close()
    with pytest.raises(ValueError):
        extract_document(data, use_ai=False)
