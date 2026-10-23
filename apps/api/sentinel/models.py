from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from sentinel.db import Base


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc)


class Principal(Base):
    __tablename__ = 'principals'
    subject: Mapped[str] = mapped_column(String(128), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class RoleBinding(Base):
    __tablename__ = 'role_bindings'
    __table_args__ = (
        UniqueConstraint('subject', 'role', 'scope_type', 'scope_id'),
        CheckConstraint("scope_type IN ('INSTITUTION','BUREAU','CASE')"),
        CheckConstraint("role IN ('MAKER','REVIEWER','AUDITOR','CLEARANCE','APPROVER','ISSUER')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject: Mapped[str] = mapped_column(ForeignKey('principals.subject'), index=True)
    role: Mapped[str] = mapped_column(String(20))
    scope_type: Mapped[str] = mapped_column(String(20))
    scope_id: Mapped[str] = mapped_column(String(64), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Institution(Base):
    __tablename__ = 'institutions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    legal_name: Mapped[str] = mapped_column(String(200))
    context: Mapped[dict] = mapped_column(JSON)
    owner: Mapped[str] = mapped_column(ForeignKey('principals.subject'))
    registry_status: Mapped[str] = mapped_column(String(32), default='DECLARED_UNVERIFIED')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Obligation(Base):
    __tablename__ = 'security_deposit_obligations'
    __table_args__ = (UniqueConstraint('id', 'institution_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), index=True)
    regulatory_event: Mapped[str] = mapped_column(String(32))
    context: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default='DECLARED')
    policy_revision: Mapped[str] = mapped_column(String(64))
    required_amount_paise: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Deposit(Base):
    __tablename__ = 'deposit_records'
    __table_args__ = (
        ForeignKeyConstraint(['obligation_id', 'institution_id'],
                             ['security_deposit_obligations.id', 'security_deposit_obligations.institution_id']),
        UniqueConstraint('id', 'institution_id'),
        UniqueConstraint('bank_code', 'reference_digest', 'hmac_version'),
        CheckConstraint('amount_paise > 0'),
        CheckConstraint('version > 0 AND input_revision > 0'),
        CheckConstraint("deposit_type IN ('FDR','RPGF','RTGS','ONLINE','OTHER_LEGACY')"),
        CheckConstraint("deposit_type != 'FDR' OR (issue_date IS NOT NULL AND maturity_date IS NOT NULL)"),
        CheckConstraint('maturity_date IS NULL OR issue_date IS NULL OR maturity_date > issue_date'),
        CheckConstraint("workflow IN ('DRAFT','PENDING_SCRUTINY','ACCEPTED')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), index=True)
    obligation_id: Mapped[str] = mapped_column(String(36), index=True)
    deposit_type: Mapped[str] = mapped_column(String(20))
    bank_code: Mapped[str] = mapped_column(String(32))
    reference_last4: Mapped[str] = mapped_column(String(4))
    reference_digest: Mapped[str] = mapped_column(String(64))
    hmac_version: Mapped[str] = mapped_column(String(32))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    issue_date: Mapped[date | None] = mapped_column(Date)
    maturity_date: Mapped[date | None] = mapped_column(Date)
    deposited_on: Mapped[date | None] = mapped_column(Date)
    workflow: Mapped[str] = mapped_column(String(24), default='DRAFT', index=True)
    verification_status: Mapped[str] = mapped_column(String(32), default='INSTITUTION_DECLARED')
    lifecycle_status: Mapped[str] = mapped_column(String(24), default='RECORDED')
    version: Mapped[int] = mapped_column(Integer, default=1)
    input_revision: Mapped[int] = mapped_column(Integer, default=1)
    maker: Mapped[str] = mapped_column(ForeignKey('principals.subject'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Document(Base):
    __tablename__ = 'documents'
    __table_args__ = (ForeignKeyConstraint(['deposit_id', 'institution_id'],
                                         ['deposit_records.id', 'deposit_records.institution_id']),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deposit_id: Mapped[str] = mapped_column(String(36), index=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), index=True)
    category: Mapped[str] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey('documents.id'))
    object_key: Mapped[str] = mapped_column(String(160), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(24), default='QUARANTINED')
    scan_result: Mapped[str | None] = mapped_column(String(160))
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    uploader: Mapped[str] = mapped_column(ForeignKey('principals.subject'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Evaluation(Base):
    __tablename__ = 'evaluations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deposit_id: Mapped[str] = mapped_column(ForeignKey('deposit_records.id'), index=True)
    input_revision: Mapped[int] = mapped_column(Integer)
    policy_revision: Mapped[str] = mapped_column(String(64))
    document_set_hash: Mapped[str] = mapped_column(String(64))
    inputs: Mapped[dict] = mapped_column(JSON)
    input_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReviewDecision(Base):
    __tablename__ = 'review_decisions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deposit_id: Mapped[str] = mapped_column(ForeignKey('deposit_records.id'), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    decision: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(2000))
    evaluation_id: Mapped[str] = mapped_column(ForeignKey('evaluations.id'))
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    detail: Mapped[dict] = mapped_column(JSON)
    request_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Outbox(Base):
    __tablename__ = 'outbox_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    aggregate_id: Mapped[str] = mapped_column(ForeignKey('documents.id'))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class IdempotencyRecord(Base):
    __tablename__ = 'idempotency_records'
    __table_args__ = (UniqueConstraint('subject', 'operation', 'key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject: Mapped[str] = mapped_column(String(128))
    operation: Mapped[str] = mapped_column(String(200))
    key: Mapped[str] = mapped_column(String(128))
    fingerprint: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
