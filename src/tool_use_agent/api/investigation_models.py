from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tool_use_agent.api.ticket_models import DiagnosisSummaryResponse
from tool_use_agent.investigations.models import (
    ApprovalDecision,
    EvidenceKind,
    InvestigationStatus,
)


class InvestigationStartRequest(BaseModel):
    supplemental_instructions: str | None = Field(default=None, min_length=1)


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    session_id: str
    status: InvestigationStatus
    started_at: datetime
    diagnosed_at: datetime | None
    completed_at: datetime | None
    stop_reason: str | None
    supplemental_instructions: str | None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: int
    kind: EvidenceKind
    title: str
    summary: str
    source_ref: str | None
    tool_audit_id: int | None
    attachment_id: int | None
    created_at: datetime


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: int
    decision: ApprovalDecision
    original_draft: str
    final_draft: str
    review_notes: str
    created_at: datetime


class InvestigationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: int
    event: str
    payload: dict[str, Any]
    created_at: datetime


class InvestigationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investigation: InvestigationResponse
    evidence: tuple[EvidenceResponse, ...]
    report: DiagnosisSummaryResponse | None
    approvals: tuple[ApprovalResponse, ...]
    events: tuple[InvestigationEventResponse, ...]


class InvestigationDecisionRequest(BaseModel):
    decision: ApprovalDecision
    final_draft: str | None = None
    review_notes: str = ""


class InvestigationDecisionResponse(BaseModel):
    investigation: InvestigationResponse
    approvals: tuple[ApprovalResponse, ...]
    should_run: bool


class DiagnosisTimeMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    count: int
    median_seconds: float | None
    p75_seconds: float | None
