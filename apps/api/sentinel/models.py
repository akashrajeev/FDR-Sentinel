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
    coverage_mode: Mapped[str] = mapped_column(String(24), default='SINGLE_RECORD', server_default='SINGLE_RECORD')
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
    release_case_id: Mapped[str | None] = mapped_column(ForeignKey('release_cases.id'), index=True)
    object_key: Mapped[str] = mapped_column(String(160), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(24), default='QUARANTINED')
    scan_result: Mapped[str | None] = mapped_column(String(160))
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    processing_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
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
    trace_context: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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


class ReleaseCase(Base):
    __tablename__ = 'release_cases'
    __table_args__ = (
        CheckConstraint("reason IN ('TERM_COMPLETED','CLOSURE','MERGER','CONVERSION','OTHER')"),
        CheckConstraint("state IN ('DRAFT','CLEARANCES_PENDING','APPROVAL_REVIEW','APPROVED_SYNTHETIC','ISSUED_SYNTHETIC')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deposit_id: Mapped[str] = mapped_column(ForeignKey('deposit_records.id'), unique=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), index=True)
    reason: Mapped[str] = mapped_column(String(24))
    policy_revision: Mapped[str] = mapped_column(String(64), default='', server_default='')
    state: Mapped[str] = mapped_column(String(32), default='DRAFT')
    required_bureaus: Mapped[list] = mapped_column(JSON, default=lambda: ['PGRC', 'VIGILANCE', 'GRANTS'])
    maker: Mapped[str] = mapped_column(String(128))
    approver: Mapped[str | None] = mapped_column(String(128))
    issuer: Mapped[str | None] = mapped_column(String(128))
    regulatory_basis: Mapped[str | None] = mapped_column(String(2000))
    version: Mapped[int] = mapped_column(Integer, default=1)
    input_revision: Mapped[int] = mapped_column(Integer, default=1)
    submitted_document_hash: Mapped[str | None] = mapped_column(String(64))
    output_document_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ClearanceDecision(Base):
    __tablename__ = 'clearance_decisions'
    __table_args__ = (UniqueConstraint('case_id', 'bureau', 'input_revision'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('release_cases.id'), index=True)
    bureau: Mapped[str] = mapped_column(String(32))
    input_revision: Mapped[int] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(String(128))
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(2000))
    evidence_document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Hold(Base):
    __tablename__ = 'holds'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('release_cases.id'), index=True)
    reason: Mapped[str] = mapped_column(String(2000))
    kind: Mapped[str] = mapped_column(String(32), default='MANUAL', server_default='MANUAL')
    required_category: Mapped[str | None] = mapped_column(String(32))
    authority: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128))
    resolution: Mapped[str | None] = mapped_column(String(2000))
    evidence_document_id: Mapped[str | None] = mapped_column(ForeignKey('documents.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Replacement(Base):
    __tablename__ = 'instrument_relationships'
    __table_args__ = (UniqueConstraint('old_deposit_id'), UniqueConstraint('new_deposit_id'),
                     CheckConstraint('old_deposit_id != new_deposit_id'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    old_deposit_id: Mapped[str] = mapped_column(ForeignKey('deposit_records.id'))
    new_deposit_id: Mapped[str] = mapped_column(ForeignKey('deposit_records.id'))
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(20), default='REQUESTED')
    maker: Mapped[str] = mapped_column(String(128))
    checker: Mapped[str | None] = mapped_column(String(128))
    rationale: Mapped[str] = mapped_column(String(2000))
    evidence_document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'), index=True)
    deposit_id: Mapped[str] = mapped_column(ForeignKey('deposit_records.id'))
    dedupe_key: Mapped[str] = mapped_column(String(160), unique=True)
    recipient: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(32))
    detail: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ExtractionCorrection(Base):
    __tablename__ = 'extraction_corrections'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey('documents.id'), index=True)
    field: Mapped[str] = mapped_column(String(32))
    value: Mapped[str] = mapped_column(String(120))
    page: Mapped[int] = mapped_column(Integer)
    bounds: Mapped[list] = mapped_column(JSON)
    quote: Mapped[str] = mapped_column(String(240))
    reason: Mapped[str] = mapped_column(String(2000))
    maker: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), default='PROPOSED')
    checker: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Discrepancy(Base):
    __tablename__ = 'discrepancies'
    __table_args__ = (UniqueConstraint('deposit_id', 'finding_key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deposit_id: Mapped[str] = mapped_column(ForeignKey('deposit_records.id'), index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey('evaluations.id'))
    finding_key: Mapped[str] = mapped_column(String(64))
    finding: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='OPEN')
    adjudicator: Mapped[str | None] = mapped_column(String(128))
    resolution: Mapped[str | None] = mapped_column(String(2000))
    evidence_document_id: Mapped[str | None] = mapped_column(ForeignKey('documents.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VerificationAttestation(Base):
    __tablename__ = 'verification_attestations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    deposit_id: Mapped[str] = mapped_column(ForeignKey('deposit_records.id'), index=True)
    source: Mapped[str] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(String(64))
    requested_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
