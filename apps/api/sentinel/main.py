import hashlib
import json
import logging
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis import Redis
from sqlalchemy import or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sentinel import services
from sentinel.auth import Actor, authenticate, require_scope
from sentinel.config import settings
from sentinel.db import get_db
from sentinel.lifecycle_api import router as lifecycle_router
from sentinel.models import AuditEvent, Deposit, Document, Institution, Obligation, Outbox, ReleaseCase
from sentinel.schemas import (
    AuditOut,
    Correction,
    DepositDetail,
    DepositIn,
    DepositOut,
    DocumentOut,
    EvaluationOut,
    InstitutionIn,
    InstitutionOut,
    ObligationIn,
    ObligationOut,
    ReviewIn,
    VersionCommand,
)
from sentinel.storage import read_original, storage
from sentinel.transactions import audit, mutate

app = FastAPI(title='FDR Sentinel', version='0.1.0',
              description='Synthetic regulatory workflow. Registration review is not bank verification or release.')
app.include_router(lifecycle_router)
logger = logging.getLogger('sentinel.http')
requests_total = Counter('sentinel_http_requests_total', 'HTTP requests', ['method', 'route', 'status'])
duration = Histogram('sentinel_http_duration_seconds', 'HTTP request duration', ['route'])


@app.middleware('http')
async def request_metadata(request: Request, call_next):
    request.state.request_id = str(uuid4())
    started = time.monotonic()
    response = await call_next(request)
    route = getattr(request.scope.get('route'), 'path', 'unmatched')
    elapsed = time.monotonic() - started
    requests_total.labels(request.method, route, str(response.status_code)).inc()
    duration.labels(route).observe(elapsed)
    response.headers['X-Request-ID'] = request.state.request_id
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    logger.info(json.dumps({'request_id': request.state.request_id, 'method': request.method,
                            'route': route, 'status': response.status_code, 'duration_ms': round(elapsed * 1000)}))
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409, content={'detail': 'Record conflicts with a uniqueness or integrity rule',
                                                  'request_id': request.state.request_id})


@app.get('/api/v1/health/live')
def live():
    return {'status': 'alive', 'environment': 'SYNTHETIC_LOCAL'}


@app.get('/api/v1/health/ready')
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text('SELECT 1'))
        if not storage().bucket_exists(settings().s3_bucket):
            raise RuntimeError('Bucket absent')
    except Exception:
        return JSONResponse(status_code=503, content={'status': 'unavailable'})
    processing = 'available'
    try:
        Redis.from_url(settings().redis_url, socket_connect_timeout=1, socket_timeout=1).ping()
    except Exception:
        processing = 'degraded_broker_unavailable'
    backlog = len(db.scalars(select(Outbox.id).where(Outbox.completed_at.is_(None)).limit(1001)).all())
    return {'status': 'ready' if processing == 'available' else 'degraded_intake_available',
            'processing': processing, 'pending_jobs_capped': backlog,
            'note': 'Broker reachability does not certify scanner or worker health'}


@app.get('/metrics', include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get('/api/v1/me')
def me(actor: Actor = Depends(authenticate)):
    return {'subject': actor.subject, 'institution_ids': actor.institution_ids(),
            'bindings': [{'role': b.role, 'scope_type': b.scope_type, 'scope_id': b.scope_id}
                         for b in actor.bindings],
            'mode': 'SYNTHETIC_LOCAL', 'external_verification': 'NOT_CONNECTED'}


@app.post('/api/v1/institutions', response_model=InstitutionOut)
def onboard(body: InstitutionIn, request: Request, actor: Actor = Depends(authenticate),
            db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: services.onboarding(db, actor, body, request.state.request_id))


@app.get('/api/v1/institutions', response_model=list[InstitutionOut])
def institutions(actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    return [services.dto(i, InstitutionOut) for i in db.scalars(select(Institution).where(
        Institution.id.in_(actor.institution_ids())).order_by(Institution.created_at.desc()).limit(100))]


@app.get('/api/v1/institutions/{institution_id}', response_model=InstitutionOut)
def institution(institution_id: str, actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    require_scope(actor, institution_id)
    record = db.get(Institution, institution_id)
    if not record:
        raise HTTPException(404, 'Resource not found')
    return services.dto(record, InstitutionOut)


@app.post('/api/v1/obligations', response_model=ObligationOut)
def obligation_create(body: ObligationIn, request: Request, actor: Actor = Depends(authenticate),
                      db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    require_scope(actor, body.institution_id, ['MAKER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: services.create_obligation(db, actor, body, request.state.request_id))


@app.get('/api/v1/obligations', response_model=list[ObligationOut])
def obligations(actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    return [services.dto(i, ObligationOut) for i in db.scalars(select(Obligation).where(
        Obligation.institution_id.in_(actor.institution_ids())).limit(100))]


@app.post('/api/v1/deposits', response_model=DepositOut)
def deposit_create(body: DepositIn, request: Request, actor: Actor = Depends(authenticate),
                   db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    obligation = db.get(Obligation, body.obligation_id)
    if not obligation:
        raise HTTPException(404, 'Resource not found')
    require_scope(actor, obligation.institution_id, ['MAKER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: services.create_deposit(db, actor, body, request.state.request_id))


@app.get('/api/v1/deposits', response_model=list[DepositOut])
def deposits(institution_id: str | None = None, actor: Actor = Depends(authenticate),
             db: Session = Depends(get_db)):
    ids = actor.institution_ids()
    if institution_id:
        require_scope(actor, institution_id)
        ids = [institution_id]
    case_deposits = select(ReleaseCase.deposit_id).where(ReleaseCase.id.in_(actor.case_ids()))
    return [services.dto(i, DepositOut) for i in db.scalars(select(Deposit).where(
        or_(Deposit.institution_id.in_(ids), Deposit.id.in_(case_deposits))).order_by(
        Deposit.created_at.desc()).limit(100))]


@app.get('/api/v1/deposits/{deposit_id}', response_model=DepositDetail)
def deposit_detail(deposit_id: str, actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    return services.detail(db, actor, deposit_id)


@app.post('/api/v1/deposits/{deposit_id}/documents', response_model=DocumentOut)
def document_upload(deposit_id: str, request: Request, file: UploadFile = File(...),
                          category: str = Form('DEPOSIT_PROOF'), supersedes_id: str | None = Form(None),
                          actor: Actor = Depends(authenticate),
                          db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    services.get_deposit(db, actor, deposit_id, roles=['MAKER'])
    if category not in ('DEPOSIT_PROOF', 'REQUEST_LETTER', 'AFFIDAVIT_6', 'APPROVAL_LETTER',
                        'CLOSURE_ORDER', 'MERGER_ORDER', 'CONVERSION_ORDER', 'SUPPORTING'):
        raise HTTPException(422, 'Unsupported document category')
    data = file.file.read(settings().max_upload_bytes + 1)
    if len(data) > settings().max_upload_bytes:
        raise HTTPException(413, 'PDF exceeds 10 MiB limit')
    if file.content_type != 'application/pdf' or not data.startswith(b'%PDF-'):
        raise HTTPException(422, 'Only PDF content with valid signature is accepted')
    fingerprint = {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data), 'category': category,
                   'supersedes_id': supersedes_id}
    return mutate(db, actor, request, idempotency_key, fingerprint,
                  lambda: services.upload(db, actor, deposit_id, data, category, request.state.request_id,
                                          supersedes_id=supersedes_id))


@app.get('/api/v1/documents/{document_id}/content')
def document_content(document_id: str, request: Request, actor: Actor = Depends(authenticate),
                     db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, 'Resource not found')
    services.get_deposit(db, actor, document.deposit_id)
    if document.status != 'READY':
        raise HTTPException(409, 'Document quarantined or unavailable')
    try:
        data = read_original(document.object_key)
        if hashlib.sha256(data).hexdigest() != document.sha256:
            raise RuntimeError('Integrity mismatch')
    except Exception:
        raise HTTPException(503, 'Document unavailable') from None
    audit(db, document.institution_id, actor.subject, 'DOCUMENT_DOWNLOADED', document.deposit_id,
          {'document_id': document.id}, request.state.request_id)
    db.commit()
    return Response(data, media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{document.id}.pdf"'})


def command_access(db, actor, deposit_id, roles):
    services.get_deposit(db, actor, deposit_id, roles=roles)


@app.post('/api/v1/deposits/{deposit_id}/correct', response_model=DepositOut)
def correction(deposit_id: str, body: Correction, request: Request, actor: Actor = Depends(authenticate),
               db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    command_access(db, actor, deposit_id, ['MAKER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: services.correct(db, actor, deposit_id, body, request.state.request_id))


@app.post('/api/v1/deposits/{deposit_id}/evaluate', response_model=EvaluationOut)
def evaluation(deposit_id: str, body: VersionCommand, request: Request, actor: Actor = Depends(authenticate),
               db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    command_access(db, actor, deposit_id, ['MAKER', 'REVIEWER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: services.run_evaluation(db, actor, deposit_id, body, request.state.request_id))


@app.post('/api/v1/deposits/{deposit_id}/submit', response_model=DepositOut)
def submission(deposit_id: str, body: VersionCommand, request: Request, actor: Actor = Depends(authenticate),
               db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    command_access(db, actor, deposit_id, ['MAKER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: services.submit(db, actor, deposit_id, body, request.state.request_id))


@app.post('/api/v1/deposits/{deposit_id}/review', response_model=DepositOut)
def review_command(deposit_id: str, body: ReviewIn, request: Request, actor: Actor = Depends(authenticate),
                   db: Session = Depends(get_db), idempotency_key: str | None = Header(None)):
    command_access(db, actor, deposit_id, ['REVIEWER'])
    return mutate(db, actor, request, idempotency_key, body.model_dump(mode='json'),
                  lambda: services.review(db, actor, deposit_id, body, request.state.request_id))


@app.get('/api/v1/work-queue', response_model=list[DepositOut])
def work_queue(actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    ids = [i for i in actor.institution_ids() if actor.allows('REVIEWER', 'INSTITUTION', i)]
    return [services.dto(d, DepositOut) for d in db.scalars(select(Deposit).where(
        Deposit.institution_id.in_(ids), Deposit.workflow == 'PENDING_SCRUTINY').limit(100))]


@app.get('/api/v1/audit-events', response_model=list[AuditOut])
def audits(actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    return [services.dto(d, AuditOut) for d in db.scalars(select(AuditEvent).where(
        AuditEvent.institution_id.in_(actor.institution_ids())).order_by(AuditEvent.created_at.desc()).limit(100))]
