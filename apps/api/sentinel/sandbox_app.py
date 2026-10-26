"""Real HTTP sandbox with independently persisted fictional records; no bank authority."""
import hashlib
import hmac
import json
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text


class SandboxSettings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')
    sandbox_database_url: str
    sandbox_api_key: str = Field(min_length=32, repr=False)
    sandbox_admin_key: str = Field(min_length=32, repr=False)
    sandbox_signing_key: str = Field(min_length=32, repr=False)


@lru_cache
def config():
    return SandboxSettings()


@lru_cache
def engine():
    return create_engine(config().sandbox_database_url, pool_pre_ping=True)


def access(authorization: str = Header('')):
    supplied = authorization.removeprefix('Bearer ')
    if not hmac.compare_digest(supplied, config().sandbox_api_key):
        raise HTTPException(401, 'Sandbox client credential required')


def administrator(authorization: str = Header('')):
    if not hmac.compare_digest(authorization.removeprefix('Bearer '), config().sandbox_admin_key):
        raise HTTPException(403, 'Separate sandbox fixture administrator required')


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class RegistryFixture(Strict):
    id: str = Field(pattern=r'^SYNTHETIC-[A-Za-z0-9-]{3,48}$')
    legal_name: str = Field(min_length=3, max_length=200)
    programme: str = Field(min_length=3, max_length=64)
    governance: Literal['PRIVATE', 'GOVERNMENT', 'GOVERNMENT_AIDED'] = 'PRIVATE'
    approval_from: date
    approval_until: date
    approval_status: Literal['ACTIVE', 'WITHDRAWN'] = 'ACTIVE'


class LedgerFixture(Strict):
    id: str = Field(pattern=r'^SB-[A-Za-z0-9-]{3,55}$')
    institution_external_id: str = Field(pattern=r'^SYNTHETIC-[A-Za-z0-9-]{3,48}$')
    bank_code: str = Field(pattern=r'^SYN(?:THETIC)?-[A-Z0-9-]{2,24}$', max_length=32)
    reference_last4: str = Field(pattern=r'^[A-Z0-9]{4}$')
    deposit_type: Literal['FDR', 'RPGF', 'RTGS', 'ONLINE']
    amount_paise: int = Field(strict=True, gt=0, le=1_000_000_000_000)
    issue_date: date | None = None
    maturity_date: date | None = None
    deposited_on: date | None = None
    status: Literal['ACTIVE', 'HOLD', 'CANCELLED'] = 'ACTIVE'


class Exchange(Strict):
    client_key: str = Field(min_length=8, max_length=128)
    operation: Literal['BANK_VERIFY', 'REGISTRY_LOOKUP', 'CASE_SYNC', 'RELEASE_ACK']
    ledger_id: str | None = Field(default=None, pattern=r'^SB-[A-Za-z0-9-]{3,55}$')
    institution_external_id: str = Field(pattern=r'^SYNTHETIC-[A-Za-z0-9-]{3,48}$')
    expected: dict
    case_id: str | None = None
    issued_output_sha256: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    human_issuer: str | None = None
    behavior: Literal['NORMAL', 'DELAYED', 'TRANSIENT_FAILURE'] = 'NORMAL'


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode()


def signed(payload):
    payload = {**payload, 'source': 'INDEPENDENT_SYNTHETIC_SANDBOX',
               'signed_at': datetime.now(timezone.utc).isoformat(), 'protocol': 'sentinel-sandbox-v1'}
    return {'payload': payload, 'signature': hmac.new(config().sandbox_signing_key.encode(),
                                                    canonical(payload), hashlib.sha256).hexdigest()}


app = FastAPI(title='FDR Sentinel — independent bank / AICTE sandbox',
    description='Fictional ledger and registry. No real institution, approval or payment authority.',
    telemetry={'tracing': False, 'metrics': False, 'logs': False})


@app.get('/health')
def health():
    with engine().connect() as db:
        db.execute(text('SELECT 1 FROM sandbox.registry LIMIT 1'))
    return {'mode': 'SYNTHETIC_SANDBOX', 'status': 'ready'}


@app.get('/v1/catalogue', dependencies=[Depends(access)])
def catalogue():
    with engine().connect() as db:
        registry = [dict(r.data) for r in db.execute(text('SELECT data FROM sandbox.registry ORDER BY id LIMIT 200'))]
        ledger = [{**r.data, 'reserved_release_case': r.release_case_id} for r in db.execute(
            text('SELECT data,release_case_id FROM sandbox.ledger ORDER BY id LIMIT 200'))]
    return {'mode': 'SYNTHETIC_SANDBOX', 'registry': registry, 'ledger': ledger}


def add_fixture(table, body):
    data = body.model_dump(mode='json')
    with engine().begin() as db:
        # Table is a source-code constant, never caller-controlled.
        existing = db.execute(text(f'SELECT data FROM sandbox.{table} WHERE id=:id'), {'id': body.id}).scalar()
        if existing and existing != data:
            raise HTTPException(409, 'Fixture is immutable; create a new fictional identity')
        db.execute(text(f'INSERT INTO sandbox.{table}(id,data) VALUES (:id,CAST(:data AS jsonb)) '
                        'ON CONFLICT (id) DO NOTHING'), {'id': body.id, 'data': json.dumps(data)})
    return {'id': body.id, 'data': data, 'mode': 'SYNTHETIC_SANDBOX'}


@app.post('/v1/fixtures/registry', dependencies=[Depends(administrator)])
def registry_fixture(body: RegistryFixture):
    if body.approval_until <= body.approval_from:
        raise HTTPException(422, 'Approval dates must be ordered')
    return add_fixture('registry', body)


@app.post('/v1/fixtures/ledger', dependencies=[Depends(administrator)])
def ledger_fixture(body: LedgerFixture):
    if body.deposit_type == 'FDR' and (not body.issue_date or not body.maturity_date
                                      or body.maturity_date <= body.issue_date):
        raise HTTPException(422, 'FDR dates required and ordered')
    if body.deposit_type in ('RTGS', 'ONLINE') and not body.deposited_on:
        raise HTTPException(422, 'Deposit date required')
    return add_fixture('ledger', body)


def determine(db, body):
    if body.operation == 'REGISTRY_LOOKUP':
        observed = db.execute(text('SELECT data FROM sandbox.registry WHERE id=:id'),
                              {'id': body.institution_external_id}).scalar()
        differences = [k for k, value in body.expected.items() if observed and observed.get(k) != value]
        outcome = 'NOT_FOUND' if not observed else 'MISMATCH' if differences else 'MATCH'
        if observed and (observed['approval_status'] != 'ACTIVE'
                         or observed['approval_until'] < datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()):
            outcome = 'APPROVAL_INACTIVE'
        return {'outcome': outcome, 'observed': observed, 'differences': differences}
    if body.operation == 'CASE_SYNC':
        return {'outcome': 'CASE_RECEIVED', 'external_case_number': 'SB-CASE-' + str(uuid4()),
                'portal_case_id': body.case_id, 'observed': {'stage': body.expected.get('stage')},
                'note': 'Receipt of portal state only; no regulator decision is fabricated'}
    row = db.execute(text('SELECT data,release_case_id FROM sandbox.ledger WHERE id=:id FOR UPDATE'),
                     {'id': body.ledger_id}).first()
    observed = dict(row.data) if row else None
    differences = [k for k, value in body.expected.items() if observed and observed.get(k) != value]
    if observed and observed['institution_external_id'] != body.institution_external_id:
        differences.append('institution_external_id')
    outcome = 'NOT_FOUND' if not observed else 'MISMATCH' if differences else 'MATCH'
    if observed and (observed['status'] != 'ACTIVE' or row.release_case_id):
        outcome = 'NOT_ACTIVE'
    if body.operation == 'RELEASE_ACK':
        if not body.case_id or not body.issued_output_sha256 or not body.human_issuer:
            raise HTTPException(422, 'Human-issued output identity and hash required')
        if row and row.release_case_id == body.case_id:
            outcome = 'MATCH'
        if outcome == 'MATCH':
            db.execute(text('UPDATE sandbox.ledger SET release_case_id=:case WHERE id=:id'),
                       {'case': body.case_id, 'id': body.ledger_id})
            outcome = 'SANDBOX_COMPLETED'
        else:
            outcome = 'SANDBOX_REJECTED_' + outcome
    return {'outcome': outcome, 'observed': observed, 'differences': sorted(set(differences)),
            'no_real_funds': True}


@app.post('/v1/requests', dependencies=[Depends(access)])
def request_exchange(body: Exchange):
    payload = body.model_dump(mode='json')
    fingerprint = hashlib.sha256(canonical(payload)).hexdigest()
    with engine().begin() as db:
        lock = int.from_bytes(hashlib.sha256(body.client_key.encode()).digest()[:8], 'big', signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock})
        existing = db.execute(text('SELECT id,fingerprint FROM sandbox.requests WHERE client_key=:key'),
                              {'key': body.client_key}).first()
        if existing:
            if existing.fingerprint != fingerprint:
                raise HTTPException(409, 'Sandbox idempotency content mismatch')
            remote_id = existing.id
        else:
            remote_id = str(uuid4())
            result = determine(db, body)
            db.execute(text('INSERT INTO sandbox.requests(id,client_key,fingerprint,payload,result,ready_at,fault_remaining) '
                            'VALUES (:id,:key,:fingerprint,CAST(:payload AS jsonb),CAST(:result AS jsonb),:ready,:fault)'),
                       {'id': remote_id, 'key': body.client_key, 'fingerprint': fingerprint,
                        'payload': json.dumps(payload), 'result': json.dumps(result),
                        'ready': datetime.now(timezone.utc) + timedelta(seconds=8 if body.behavior == 'DELAYED' else 0),
                        'fault': 1 if body.behavior == 'TRANSIENT_FAILURE' else 0})
    return signed({'remote_id': remote_id, 'client_key': body.client_key, 'fingerprint': fingerprint, 'state': 'PENDING'})


@app.get('/v1/requests/{request_id}', dependencies=[Depends(access)])
def poll(request_id: str):
    fail = False
    with engine().begin() as db:
        row = db.execute(text('SELECT * FROM sandbox.requests WHERE id=:id FOR UPDATE'), {'id': request_id}).first()
        if not row:
            raise HTTPException(404, 'Sandbox request not found')
        if row.fault_remaining:
            db.execute(text('UPDATE sandbox.requests SET fault_remaining=fault_remaining-1 WHERE id=:id'), {'id': request_id})
            fail = True
        payload = {'remote_id': row.id, 'client_key': row.client_key, 'fingerprint': row.fingerprint,
                   'state': 'PENDING' if row.ready_at > datetime.now(timezone.utc) else 'COMPLETED',
                   'result': row.result if row.ready_at <= datetime.now(timezone.utc) else None}
    if fail:
        raise HTTPException(503, 'Injected transient sandbox failure; persisted request retained')
    return signed(payload)
