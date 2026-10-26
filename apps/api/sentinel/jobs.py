import hashlib
import logging
from datetime import timedelta

from celery import Celery
from celery.signals import worker_process_init
from redis import Redis
from sqlalchemy import or_, select
from sqlalchemy.engine import make_url

from sentinel.config import settings
from sentinel.db import session_factory
from sentinel.extraction import extract_document, render_previews
from sentinel.models import Deposit, Document, Outbox, ReleaseCase, now
from sentinel.storage import put_blob, read_original, scan_bytes
from sentinel.telemetry import configure, traced
from sentinel.transactions import audit

celery = Celery('sentinel', broker=settings().redis_url)
celery.conf.update(
    task_default_queue='sentinel-' + make_url(settings().database_url).database,
    task_serializer='json', accept_content=['json'], result_serializer='json',
    task_acks_late=True, worker_prefetch_multiplier=1,
    task_time_limit=120, task_soft_time_limit=100, broker_connection_retry_on_startup=True,
    broker_transport_options={'visibility_timeout': 300},
    beat_schedule={'outbox': {'task': 'sentinel.publish_outbox', 'schedule': 3.0},
                   'integrations': {'task': 'sentinel.integration_work', 'schedule': 2.0},
                   'maturity': {'task': 'sentinel.maturity', 'schedule': 3600.0}},
)
logger = logging.getLogger(__name__)


@celery.task(name='sentinel.integration_work')
def integration_work():
    from sentinel.delivery import process_deliveries
    from sentinel.integrations import process_pending
    return {'integrations': process_pending(), 'notifications': process_deliveries()}


@worker_process_init.connect
def initialize_worker_telemetry(**kwargs):
    configure('sentinel-worker')


@celery.task(name='sentinel.maturity')
def scheduled_maturity():
    from sentinel.lifecycle import run_maturity, today
    with session_factory()() as db:
        result = run_maturity(db, today())
        db.commit()
        return result


@celery.task(name='sentinel.publish_outbox')
@traced('outbox.publish')
def publish_outbox():
    Redis.from_url(settings().redis_url, socket_connect_timeout=2, socket_timeout=2).set(
        'sentinel:heartbeat:' + make_url(settings().database_url).database, now().isoformat(), ex=30)
    # Republish uncompleted events after 5 min to recover a crash after broker acceptance.
    with session_factory()() as db:
        events = db.scalars(select(Outbox).where(
            Outbox.completed_at.is_(None), Outbox.dead_lettered_at.is_(None), or_(Outbox.published_at.is_(None),
                                             Outbox.published_at < now() - timedelta(minutes=5)),
        ).order_by(Outbox.created_at).with_for_update(skip_locked=True).limit(20)).all()
        for event in events:
            process_document.apply_async(args=[event.id], task_id=event.id, headers=event.trace_context, retry=False)
            event.published_at = now()
            event.attempts += 1
        db.commit()
        return len(events)


@celery.task(name='sentinel.process_document', bind=True, max_retries=5)
@traced('document.process')
def process_document(self, event_id):
    with session_factory()() as db:
        event = db.get(Outbox, event_id)
        if not event or event.completed_at or event.dead_lettered_at:
            return 'ALREADY_COMPLETED'
        document = db.get(Document, event.aggregate_id)
        # Same lock order as API: deposit -> document -> event.
        deposit = db.scalar(select(Deposit).where(Deposit.id == document.deposit_id).with_for_update())
        document = db.scalar(select(Document).where(Document.id == document.id).with_for_update()
                             .execution_options(populate_existing=True))
        event = db.scalar(select(Outbox).where(Outbox.id == event_id).with_for_update()
                          .execution_options(populate_existing=True))
        if event.completed_at or event.dead_lettered_at:
            return 'ALREADY_COMPLETED'
        event.processing_attempts += 1
        try:
            data = read_original(document.object_key)
            if hashlib.sha256(data).hexdigest() != document.sha256:
                raise ValueError('Stored object digest mismatch')
            scan = scan_bytes(data)
            if scan != 'CLEAN':
                document.status = 'REJECTED'
                document.scan_result = 'ClamAV: INFECTED'
            else:
                document.evidence, document.processing_metadata = extract_document(data)
                preview_hashes = {}
                for page_number, png in render_previews(data).items():
                    put_blob(f'previews/{document.id}/{page_number}.png', png, 'image/png')
                    preview_hashes[str(page_number)] = hashlib.sha256(png).hexdigest()
                document.processing_metadata = {**document.processing_metadata, 'preview_hashes': preview_hashes}
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
            if event.processing_attempts >= 5:
                event.dead_lettered_at = now()
                document.scan_result = 'DEAD_LETTER: processor failed five attempts; officer retry required'
            document.processing_metadata = {**document.processing_metadata, 'last_failure_type': type(exc).__name__,
                                             'processing_attempts': event.processing_attempts}
            deposit.version += 1
            audit(db, deposit.institution_id, 'worker', 'DOCUMENT_PROCESSING_FAILED', deposit.id,
                  {'document_id': document.id, 'event_id': event.id}, event.id)
            db.commit()
            logger.warning('document_processing_failed event_id=%s error_type=%s', event_id, type(exc).__name__)
            if event.dead_lettered_at:
                return 'DEAD_LETTER'
            raise self.retry(exc=RuntimeError('Document processor unavailable'), countdown=15 * (self.request.retries + 1))
        deposit.version += 1
        if document.release_case_id:
            case = db.scalar(select(ReleaseCase).where(ReleaseCase.id == document.release_case_id).with_for_update())
            case.version += 1
        audit(db, deposit.institution_id, 'worker', 'DOCUMENT_' + document.status, deposit.id,
              {'document_id': document.id, 'event_id': event.id, 'sha256': document.sha256}, event.id)
        db.commit()
        return document.status
