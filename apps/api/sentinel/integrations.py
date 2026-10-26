"""Durable authenticated sandbox exchanges; never grants financial/regulatory authority."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from sqlalchemy import select
from sqlalchemy.engine import make_url

from sentinel.config import settings
from sentinel.db import session_factory
from sentinel.models import Deposit, Document, Institution, IntegrationRequest, now, uid
from sentinel.telemetry import capture_context, propagator
from sentinel.transactions import audit


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def call_sandbox(method, path, payload=None):
    config = settings()
    parsed = urlparse(config.sandbox_url)
    if (not config.synthetic_mode or config.environment != 'development'
            or parsed.hostname not in ('sandbox', 'localhost', '127.0.0.1')
            or parsed.scheme != 'http' or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise RuntimeError('Local sandbox transport only')
    if len(config.sandbox_api_key) < 32 or len(config.sandbox_signing_key) < 32:
        raise RuntimeError('Sandbox credentials unavailable')
    with httpx.Client(timeout=5, trust_env=False, follow_redirects=False) as client:
        response = client.request(method, config.sandbox_url.rstrip('/') + path, json=payload,
                                  headers={'Authorization': 'Bearer ' + config.sandbox_api_key, **capture_context()})
    response.raise_for_status()
    if len(response.content) > 512 * 1024:
        raise ValueError('Sandbox response exceeds bound')
    return response.json()


def verified(envelope, request):
    payload, signature = envelope['payload'], envelope['signature']
    expected_signature = hmac.new(settings().sandbox_signing_key.encode(), canonical(payload), hashlib.sha256).hexdigest()
    if not isinstance(signature, str) or not hmac.compare_digest(signature, expected_signature):
        raise ValueError('Invalid sandbox response signature')
    signed_at = datetime.fromisoformat(payload['signed_at'])
    if signed_at.tzinfo is None or abs((now() - signed_at).total_seconds()) > 300:
        raise ValueError('Stale sandbox response')
    if (payload['source'] != 'INDEPENDENT_SYNTHETIC_SANDBOX' or payload['protocol'] != 'sentinel-sandbox-v1'
            or payload['client_key'] != request.payload['client_key']
            or payload['fingerprint'] != hashlib.sha256(canonical(request.payload)).hexdigest()
            or (request.remote_id and payload['remote_id'] != request.remote_id)
            or payload['state'] not in ('PENDING', 'COMPLETED')):
        raise ValueError('Sandbox correlation/content mismatch')
    return payload, signature


def expected_deposit(deposit):
    return {key: getattr(deposit, key).isoformat() if hasattr(getattr(deposit, key), 'isoformat')
            else getattr(deposit, key) for key in ('amount_paise', 'bank_code', 'reference_last4',
                                                 'deposit_type', 'issue_date', 'maturity_date', 'deposited_on')}


def enqueue(db, actor, institution, operation, behavior='NORMAL', deposit=None, case=None, ledger_id=None):
    if not institution.external_id.startswith('SYNTHETIC-'):
        raise HTTPException(422, 'Sandbox lookup requires a fictional SYNTHETIC- institution identifier')
    request = IntegrationRequest(id=uid(), institution_id=institution.id, deposit_id=deposit.id if deposit else None,
        case_id=case.id if case else None, operation=operation, requested_by=actor.subject,
        input_revision=deposit.input_revision if deposit else 1, payload={}, trace_context=capture_context())
    expected = expected_deposit(deposit) if deposit else {
        'legal_name': institution.legal_name, 'programme': institution.context['programme'],
        'governance': institution.context['governance']}
    if operation == 'CASE_SYNC':
        expected = {'stage': case.state}
    payload = {'client_key': make_url(settings().database_url).database + ':' + request.id,
        'operation': operation, 'ledger_id': ledger_id, 'institution_external_id': institution.external_id,
        'expected': expected, 'case_id': case.id if case else None, 'issued_output_sha256': None,
        'human_issuer': None, 'behavior': behavior}
    if operation == 'RELEASE_ACK':
        output = db.get(Document, case.output_document_id)
        payload.update(issued_output_sha256=output.sha256, human_issuer=case.issuer)
    request.payload = payload
    db.add(request)
    db.flush()
    audit(db, institution.id, actor.subject, 'SANDBOX_' + operation + '_QUEUED', request.id,
          {'deposit_id': request.deposit_id, 'case_id': request.case_id, 'no_financial_authority': True}, request.id)
    return dto(request)


def dto(request):
    return {'id': request.id, 'institution_id': request.institution_id, 'deposit_id': request.deposit_id,
            'case_id': request.case_id, 'operation': request.operation, 'state': request.state,
            'attempts': request.attempts, 'last_error': request.last_error, 'result': request.result,
            'remote_id': request.remote_id, 'input_revision': request.input_revision,
            'created_at': request.created_at.isoformat(), 'mode': 'SANDBOX_NOT_OFFICIAL',
            'ledger_id': request.payload.get('ledger_id')}


def result_blockers(db, deposit):
    requests = db.scalars(select(IntegrationRequest).where(
        IntegrationRequest.institution_id == deposit.institution_id,
        IntegrationRequest.operation.in_(['BANK_VERIFY', 'REGISTRY_LOOKUP']),
        (IntegrationRequest.deposit_id == deposit.id) | (IntegrationRequest.deposit_id.is_(None))
    ).order_by(IntegrationRequest.created_at.desc(), IntegrationRequest.id.desc())).all()
    seen, blockers = set(), []
    for request in requests:
        if request.operation in seen:
            continue
        seen.add(request.operation)
        if request.operation == 'BANK_VERIFY' and request.input_revision != deposit.input_revision:
            blockers.append('Sandbox bank result is stale; request verification for current inputs')
        elif request.state != 'SUCCEEDED':
            blockers.append(f'{request.operation} sandbox request is {request.state}; completion required')
        elif request.result['outcome'] != 'MATCH':
            blockers.append(f"{request.operation} sandbox outcome: {request.result['outcome']}")
    return blockers


def process_one(request_id):
    with session_factory()() as db, db.no_autoflush:
        # Same aggregate lock order as decision/worker paths.
        initial = db.get(IntegrationRequest, request_id)
        if not initial:
            return 'MISSING'
        if initial.deposit_id:
            db.scalar(select(Deposit).where(Deposit.id == initial.deposit_id).with_for_update())
        request = db.scalar(select(IntegrationRequest).where(IntegrationRequest.id == request_id)
                            .with_for_update().execution_options(populate_existing=True))
        if request.state in ('SUCCEEDED', 'STALE', 'DEAD_LETTER'):
            return request.state
        with trace.get_tracer('sentinel').start_as_current_span('sandbox.exchange',
                context=propagator.extract(request.trace_context), record_exception=False,
                set_status_on_exception=False) as span:
            request.attempts += 1
            try:
                if not request.remote_id:
                    payload, _ = verified(call_sandbox('POST', '/v1/requests', request.payload), request)
                    request.remote_id = payload['remote_id']
                payload, signature = verified(call_sandbox('GET', '/v1/requests/' + request.remote_id), request)
                request.last_error = None
                if payload['state'] == 'PENDING':
                    if (now() - request.created_at).total_seconds() > 120:
                        raise TimeoutError('Sandbox response deadline exceeded')
                    request.state = 'WAITING'
                else:
                    result = payload['result']
                    allowed = {'MATCH', 'MISMATCH', 'NOT_FOUND', 'NOT_ACTIVE', 'APPROVAL_INACTIVE', 'CASE_RECEIVED',
                               'SANDBOX_COMPLETED', 'SANDBOX_REJECTED_NOT_FOUND', 'SANDBOX_REJECTED_MISMATCH',
                               'SANDBOX_REJECTED_NOT_ACTIVE'}
                    if not isinstance(result, dict) or result.get('outcome') not in allowed:
                        raise ValueError('Invalid sandbox result contract')
                    request.result, request.signature = result, signature
                    request.state = 'SUCCEEDED'
                    if request.deposit_id and db.get(Deposit, request.deposit_id).input_revision != request.input_revision:
                        request.state = 'STALE'
                    if request.operation == 'REGISTRY_LOOKUP':
                        institution = db.get(Institution, request.institution_id)
                        institution.registry_status = 'SANDBOX_' + result['outcome']
                    request.completed_at = now()
                    audit(db, request.institution_id, 'integration-worker', 'SANDBOX_RESPONSE_RECORDED', request.id,
                          {'operation': request.operation, 'outcome': result['outcome'], 'state': request.state,
                           'source': 'INDEPENDENT_SYNTHETIC_SANDBOX', 'remote_id': request.remote_id,
                           'signature_verified': True, 'no_real_funds': True}, request.id)
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR))
                span.set_attribute('error.type', type(exc).__name__)
                request.last_error = type(exc).__name__
                request.state = 'DEAD_LETTER' if request.attempts >= 5 else 'WAITING'
                audit(db, request.institution_id, 'integration-worker', 'SANDBOX_EXCHANGE_FAILED', request.id,
                      {'error_type': request.last_error, 'state': request.state}, request.id)
            request.next_attempt_at = now() + timedelta(seconds=min(30, max(2, request.attempts * 2)))
            db.commit()
            return request.state


def process_pending():
    with session_factory()() as db:
        ids = list(db.scalars(select(IntegrationRequest.id).where(
            IntegrationRequest.state.in_(['PENDING', 'WAITING']), IntegrationRequest.next_attempt_at <= now()
        ).order_by(IntegrationRequest.created_at).limit(10)))
    return [process_one(identity) for identity in ids]


def require_no_blockers(db, deposit):
    blockers = result_blockers(db, deposit)
    if blockers:
        raise HTTPException(409, '; '.join(blockers))
