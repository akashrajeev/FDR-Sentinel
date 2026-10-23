import hashlib
import logging
from datetime import timedelta

from celery import Celery
from sqlalchemy import or_, select

from sentinel.config import settings
from sentinel.db import session_factory
from sentinel.document_pipeline import validate_and_extract
from sentinel.models import Deposit, Document, Outbox, now
from sentinel.storage import read_original, scan_bytes
from sentinel.transactions import audit

celery = Celery('sentinel', broker=settings().redis_url)
celery.conf.update(
    task_serializer='json', accept_content=['json'], result_serializer='json',
    task_acks_late=True, worker_prefetch_multiplier=1,
    task_time_limit=120, task_soft_time_limit=100, broker_connection_retry_on_startup=True,
    broker_transport_options={'visibility_timeout': 300},
    beat_schedule={'outbox': {'task': 'sentinel.publish_outbox', 'schedule': 3.0}},
)
logger = logging.getLogger(__name__)


@celery.task(name='sentinel.publish_outbox')
def publish_outbox():
    # Republish uncompleted events after 5 min to recover a crash after broker acceptance.
    with session_factory()() as db:
        events = db.scalars(select(Outbox).where(
            Outbox.completed_at.is_(None), or_(Outbox.published_at.is_(None),
                                             Outbox.published_at < now() - timedelta(minutes=5)),
        ).order_by(Outbox.created_at).with_for_update(skip_locked=True).limit(20)).all()
        for event in events:
            process_document.apply_async(args=[event.id], task_id=event.id, retry=False)
            event.published_at = now()
            event.attempts += 1
        db.commit()
        return len(events)


@celery.task(name='sentinel.process_document', bind=True, max_retries=5)
def process_document(self, event_id):
    with session_factory()() as db:
        event = db.get(Outbox, event_id)
        if not event or event.completed_at:
            return 'ALREADY_COMPLETED'
        document = db.get(Document, event.aggregate_id)
        # Same lock order as API: deposit -> document -> event.
        deposit = db.scalar(select(Deposit).where(Deposit.id == document.deposit_id).with_for_update())
        document = db.scalar(select(Document).where(Document.id == document.id).with_for_update())
        event = db.scalar(select(Outbox).where(Outbox.id == event_id).with_for_update())
        if event.completed_at:
            return 'ALREADY_COMPLETED'
        try:
            data = read_original(document.object_key)
            if hashlib.sha256(data).hexdigest() != document.sha256:
                raise ValueError('Stored object digest mismatch')
            scan = scan_bytes(data)
            if scan != 'CLEAN':
                document.status = 'REJECTED'
                document.scan_result = 'ClamAV: INFECTED'
            else:
                document.evidence = validate_and_extract(data)
                document.status = 'READY'
                document.scan_result = 'ClamAV INSTREAM: CLEAN'
            event.completed_at = now()
        except ValueError:
            document.status = 'REJECTED'
            document.scan_result = 'Invalid or unsupported PDF / digest mismatch'
            event.completed_at = now()
        except Exception as exc:
            document.status = 'FAILED'
            document.scan_result = 'Processing unavailable; quarantined, retry pending'
            deposit.version += 1
            audit(db, deposit.institution_id, 'worker', 'DOCUMENT_PROCESSING_FAILED', deposit.id,
                  {'document_id': document.id, 'event_id': event.id}, event.id)
            db.commit()
            logger.warning('document_processing_failed event_id=%s error_type=%s', event_id, type(exc).__name__)
            raise self.retry(exc=RuntimeError('Document processor unavailable'), countdown=15 * (self.request.retries + 1))
        deposit.version += 1
        audit(db, deposit.institution_id, 'worker', 'DOCUMENT_' + document.status, deposit.id,
              {'document_id': document.id, 'event_id': event.id, 'sha256': document.sha256}, event.id)
        db.commit()
        return document.status
