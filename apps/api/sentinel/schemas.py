from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class PolicyContext(StrictModel):
    academic_year: str = Field(pattern=r'^20\d{2}-\d{2}$')
    governance: Literal['PRIVATE', 'GOVERNMENT', 'GOVERNMENT_AIDED', 'UNKNOWN']
    programme: Literal['ENGINEERING_UG', 'ENGINEERING', 'PLANNING', 'APPLIED_ARTS', 'DESIGN', 'HMCT',
                       'COMPUTER_APPLICATIONS', 'MANAGEMENT', 'OTHER', 'UNKNOWN']
    level: Literal['DIPLOMA', 'UG', 'PG', 'UNKNOWN'] = 'UG'
    land: Literal['OWNED', 'PRIVATE_LEASE', 'OTHER', 'UNKNOWN']
    exceptional_context: bool = True


class InstitutionIn(StrictModel):
    external_id: str = Field(min_length=5, max_length=64, pattern=r'^[A-Za-z0-9-]+$')
    legal_name: str = Field(min_length=3, max_length=200)
    context: PolicyContext


class InstitutionOut(InstitutionIn):
    id: str
    registry_status: str


class ObligationIn(StrictModel):
    institution_id: str
    regulatory_event: Literal['NEW_INSTITUTION', 'HISTORICAL_RECORD', 'OTHER']
    coverage_mode: Literal['SINGLE_RECORD', 'AGGREGATE_REVIEW'] = 'SINGLE_RECORD'


class ObligationOut(ObligationIn):
    id: str
    context: PolicyContext
    status: str
    policy_revision: str
    required_amount_paise: int | None


class DepositValues(StrictModel):
    amount_paise: int = Field(strict=True, gt=0, le=1_000_000_000_000)
    issue_date: date | None = None
    maturity_date: date | None = None
    deposited_on: date | None = None

    @model_validator(mode='after')
    def date_order(self):
        if self.issue_date and self.maturity_date and self.maturity_date <= self.issue_date:
            raise ValueError('Maturity must be after issue date')
        return self


class DepositIn(DepositValues):
    obligation_id: str
    deposit_type: Literal['FDR', 'RPGF', 'RTGS', 'ONLINE', 'OTHER_LEGACY']
    bank_code: str = Field(min_length=3, max_length=32, pattern=r'^[A-Z0-9-]+$')
    reference: str = Field(min_length=6, max_length=80, pattern=r'^[A-Za-z0-9-]+$')

    @model_validator(mode='after')
    def type_dates(self):
        if self.deposit_type == 'FDR' and (not self.issue_date or not self.maturity_date):
            raise ValueError('FDR requires issue and maturity dates')
        if self.deposit_type in ('RTGS', 'ONLINE') and not self.deposited_on:
            raise ValueError('Online/RTGS deposit requires deposited_on')
        return self


class VersionCommand(StrictModel):
    expected_version: int = Field(strict=True, ge=1)


class Correction(DepositValues):
    expected_version: int = Field(strict=True, ge=1)


class ReviewIn(VersionCommand):
    decision: Literal['ACCEPT_REGISTRATION', 'RETURN']
    reason: str = Field(min_length=10, max_length=2000)
    evidence_reviewed: bool = False


class DepositOut(DepositValues):
    id: str
    institution_id: str
    obligation_id: str
    deposit_type: str
    bank_code: str
    reference_last4: str
    workflow: str
    verification_status: str
    lifecycle_status: str
    version: int
    input_revision: int
    created_at: datetime


class DocumentOut(StrictModel):
    id: str
    deposit_id: str
    category: str
    active: bool
    supersedes_id: str | None
    sha256: str
    size: int
    status: str
    scan_result: str | None
    evidence: list[dict[str, Any]]
    processing_metadata: dict[str, Any]


class EvaluationOut(StrictModel):
    id: str
    input_revision: int
    policy_revision: str
    document_set_hash: str
    result: dict[str, Any]
    evaluated_at: datetime


class DepositDetail(DepositOut):
    current_policy_revision: str
    evaluation_fresh: bool
    documents: list[DocumentOut]
    evaluations: list[EvaluationOut]
    decisions: list[dict[str, Any]]


class AuditOut(StrictModel):
    id: str
    institution_id: str
    actor: str
    action: str
    aggregate_id: str
    detail: dict[str, Any]
    request_id: str
    created_at: datetime


class SummaryOut(StrictModel):
    as_of: date
    mode: str
    workflow_counts: dict[str, int]
    stored_lifecycle_counts: dict[str, int]
    declared_total_paise: str
    fdr_matured_from_dates: int
    fdr_upcoming_90_days: int
    release_case_counts: dict[str, int]
    actual_financial_releases: int
    external_verification: str
    completed_synthetic_case_time: dict[str, Any]
    policy_revision: str
    policy_status: str
