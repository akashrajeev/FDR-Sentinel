import hashlib
import re

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from sentinel.auth import Actor
from sentinel.compliance import digest
from sentinel.models import AuditEvent, IdempotencyRecord


def audit(db: Session, institution_id: str, actor: str, action: str, aggregate_id: str,
          detail: dict, request_id: str):
    db.add(AuditEvent(institution_id=institution_id, actor=actor, action=action,
                      aggregate_id=aggregate_id, detail=jsonable_encoder(detail), request_id=request_id))


def mutate(db: Session, actor: Actor, request: Request, key: str | None, payload, action):
    if not key or not re.fullmatch(r'[A-Za-z0-9_.:-]{8,128}', key):
        raise HTTPException(422, 'Idempotency-Key must be 8-128 safe characters')
    operation = f'{request.method} {request.url.path}'
    fingerprint = digest(payload)
    lock = int.from_bytes(hashlib.sha256(f'{actor.subject}:{operation}:{key}'.encode()).digest()[:8],
                          'big', signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock})
    existing = db.scalar(select(IdempotencyRecord).where(
        IdempotencyRecord.subject == actor.subject, IdempotencyRecord.operation == operation,
        IdempotencyRecord.key == key))
    if existing:
        if existing.fingerprint != fingerprint:
            raise HTTPException(409, 'Idempotency key was used with different content')
        return existing.response
    response = jsonable_encoder(action())
    db.add(IdempotencyRecord(subject=actor.subject, operation=operation, key=key,
                             fingerprint=fingerprint, response=response))
    db.commit()
    return response
