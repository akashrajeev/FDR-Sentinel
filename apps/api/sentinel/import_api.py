import csv
import hashlib
import hmac
import io
import re

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from sentinel.auth import Actor, authenticate, require_scope
from sentinel.config import settings
from sentinel.db import get_db
from sentinel.models import Deposit, Obligation
from sentinel.schemas import DepositIn
from sentinel.services import create_deposit
from sentinel.transactions import mutate

router = APIRouter(prefix='/api/v1/legacy-import')
HEADERS = ['obligation_id', 'deposit_type', 'bank_code', 'reference', 'amount_paise', 'issue_date', 'maturity_date', 'deposited_on']


def parse(file, db, actor):
    data = file.file.read(200 * 1024 + 1)
    if len(data) > 200 * 1024:
        raise HTTPException(413, 'CSV limit is 200 KiB')
    try:
        reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')), strict=True)
        if reader.fieldnames != HEADERS:
            raise ValueError('CSV header must exactly match the downloadable template')
        rows, seen = [], set()
        for number, raw in enumerate(reader, 2):
            if number > 201 or None in raw or any(value is None for value in raw.values()):
                raise ValueError('At most 200 complete CSV rows are permitted')
            if not re.fullmatch(r'[0-9]+', raw['amount_paise']):
                raise ValueError(f'Row {number}: integer paise required')
            values = {key: value.strip() for key, value in raw.items() if value.strip()}
            values['amount_paise'] = int(raw['amount_paise'])
            body = DepositIn.model_validate(values)
            if not body.reference.upper().startswith('SYN-') or not body.bank_code.startswith(('SYN-', 'SYNTHETIC-')):
                raise ValueError(f'Row {number}: synthetic SYN- references/banks only')
            parent = db.get(Obligation, body.obligation_id)
            if not parent:
                raise ValueError(f'Row {number}: obligation not available')
            require_scope(actor, parent.institution_id, ['MAKER'])
            digest = hmac.new(settings().reference_hmac_key.encode(), body.reference.upper().encode(), hashlib.sha256).hexdigest()
            key = (body.bank_code, digest)
            if key in seen or db.scalar(select(Deposit.id).where(Deposit.bank_code == body.bank_code,
                Deposit.reference_digest == digest, Deposit.hmac_version == settings().reference_hmac_version)):
                raise ValueError(f'Row {number}: duplicate bank/reference')
            seen.add(key)
            rows.append(body)
        if not rows:
            raise ValueError('CSV contains no deposit records')
        return data, rows
    except (UnicodeError, csv.Error, ValueError, ValidationError) as exc:
        detail = 'CSV contains an invalid typed field or date' if isinstance(exc, ValidationError) else str(exc)
        raise HTTPException(422, detail) from None


@router.get('/template')
def template(actor: Actor = Depends(authenticate)):
    from fastapi.responses import Response
    return Response(','.join(HEADERS) + '\n', media_type='text/csv',
                    headers={'Content-Disposition': 'attachment; filename="synthetic-legacy-template.csv"'})


@router.post('/preview')
def preview(file: UploadFile = File(...), actor: Actor = Depends(authenticate), db: Session = Depends(get_db)):
    data, rows = parse(file, db, actor)
    return {'sha256': hashlib.sha256(data).hexdigest(), 'rows': len(rows),
            'declared_total_paise': str(sum(r.amount_paise for r in rows)),
            'note': 'Preview only; commit creates DRAFT records, never acceptance or bank verification'}


@router.post('/commit')
def commit(request: Request, file: UploadFile = File(...), expected_sha256: str = Form(...),
           actor: Actor = Depends(authenticate), db: Session = Depends(get_db),
           idempotency_key: str | None = Header(None)):
    data = file.file.read(200 * 1024 + 1)
    if len(data) > 200 * 1024:
        raise HTTPException(413, 'CSV limit is 200 KiB')
    digest = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(digest, expected_sha256):
        raise HTTPException(409, 'CSV changed after preview')
    def action():
        file.file = io.BytesIO(data)
        _, rows = parse(file, db, actor)
        records = [create_deposit(db, actor, row, request.state.request_id) for row in rows]
        return {'rows': len(records), 'records': records, 'sha256': digest, 'workflow': 'DRAFT'}
    return mutate(db, actor, request, idempotency_key, {'sha256': digest}, action)
