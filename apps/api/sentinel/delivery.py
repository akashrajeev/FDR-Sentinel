"""Real local SMTP transport; persistent retry and at-least-once delivery semantics."""
import hashlib
import smtplib
from datetime import timedelta
from email.message import EmailMessage

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from sentinel.config import settings
from sentinel.db import session_factory
from sentinel.models import Notification, NotificationDelivery, now, uid
from sentinel.telemetry import traced
from sentinel.transactions import audit


def ensure_delivery(db, notification_id):
    db.execute(insert(NotificationDelivery).values(id=uid(), notification_id=notification_id,
        state='PENDING', attempts=0, next_attempt_at=now(),
        message_id=f'<sentinel-{notification_id}@sentinel.invalid>').on_conflict_do_nothing())


@traced('notification.smtp')
def deliver_one(identity):
    with session_factory()() as db:
        row = db.scalar(select(NotificationDelivery).where(NotificationDelivery.id == identity).with_for_update())
        if not row or row.state != 'PENDING':
            return 'NOOP'
        notification = db.get(Notification, row.notification_id)
        row.attempts += 1
        try:
            config = settings()
            if not config.synthetic_mode or config.smtp_host not in ('mailpit', '127.0.0.1', 'localhost'):
                raise RuntimeError('Only local synthetic mailbox transport is permitted')
            message = EmailMessage()
            message['From'] = 'FDR Sentinel <notifications@sentinel.invalid>'
            recipient = hashlib.sha256(notification.recipient.encode()).hexdigest()[:16]
            message['To'] = recipient + '@sentinel.invalid'
            message['Subject'] = 'SYNTHETIC maturity alert · ' + notification.id
            message['Message-ID'] = row.message_id
            message.set_content('FDR Sentinel synthetic environment — no financial authority.\n'
                f'Deposit: {notification.deposit_id}\nDays remaining: {notification.detail.get("days_remaining")}\n'
                f'Reminder band: {notification.detail.get("threshold")} days.\n'
                'Maturity does not authorize release. Sign in to inspect your scoped evidence and workflow.')
            with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=5) as smtp:
                refused = smtp.send_message(message)
                if refused:
                    raise RuntimeError('Local mailbox refused delivery')
            row.state, row.delivered_at, row.last_error = 'SENT', now(), None
            action = 'NOTIFICATION_SMTP_ACCEPTED'
        except Exception as exc:
            trace.get_current_span().set_status(Status(StatusCode.ERROR))
            trace.get_current_span().set_attribute('error.type', type(exc).__name__)
            row.last_error = type(exc).__name__
            row.state = 'DEAD_LETTER' if row.attempts >= 5 else 'PENDING'
            row.next_attempt_at = now() + timedelta(seconds=min(60, 2 ** row.attempts))
            action = 'NOTIFICATION_SMTP_FAILED'
        audit(db, notification.institution_id, 'notification-worker', action, notification.deposit_id,
              {'notification_id': notification.id, 'message_id': row.message_id,
               'state': row.state, 'attempts': row.attempts, 'error_type': row.last_error}, notification.id)
        db.commit()
        return row.state


def process_deliveries():
    with session_factory()() as db:
        missing = list(db.scalars(select(Notification.id).outerjoin(NotificationDelivery,
            NotificationDelivery.notification_id == Notification.id).where(NotificationDelivery.id.is_(None)).limit(20)))
        for notification_id in missing:
            ensure_delivery(db, notification_id)
        db.commit()
        ids = list(db.scalars(select(NotificationDelivery.id).where(NotificationDelivery.state == 'PENDING',
            NotificationDelivery.next_attempt_at <= now()).order_by(NotificationDelivery.next_attempt_at).limit(20)))
    return [deliver_one(identity) for identity in ids]
