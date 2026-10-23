from typing import Any, Literal

from pydantic import Field

from sentinel.schemas import StrictModel, VersionCommand


class ReleaseIn(StrictModel):
    deposit_id: str
    reason: Literal['TERM_COMPLETED', 'CLOSURE', 'MERGER', 'CONVERSION', 'OTHER']


class ReleaseOut(StrictModel):
    id: str
    deposit_id: str
    institution_id: str
    reason: str
    state: str
    version: int
    input_revision: int
    required_bureaus: list[str]
    approver: str | None
    issuer: str | None
    output_document_id: str | None
    clearances: list[dict[str, Any]]
    holds: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    blockers: list[str]
    mode: str = 'SYNTHETIC_ONLY_NO_FINANCIAL_AUTHORITY'


class ClearanceIn(VersionCommand):
    decision: Literal['CLEARED', 'REJECTED']
    reason: str = Field(min_length=10, max_length=2000)
    evidence_document_id: str


class ApprovalIn(VersionCommand):
    regulatory_basis: str = Field(min_length=30, max_length=2000)
    synthetic_acknowledgement: Literal[True]


class HoldIn(VersionCommand):
    reason: str = Field(min_length=10, max_length=2000)


class HoldResolution(VersionCommand):
    resolution: str = Field(min_length=20, max_length=2000)
    evidence_document_id: str


class ReplacementIn(StrictModel):
    old_deposit_id: str
    new_deposit_id: str
    kind: Literal['REPLACEMENT', 'RENEWAL', 'AUTO_RENEWAL_RECORDED']
    rationale: str = Field(min_length=20, max_length=2000)
    evidence_document_id: str
    expected_old_version: int = Field(ge=1)


class ReplacementApproval(VersionCommand):
    policy_basis: str = Field(min_length=30, max_length=2000)
