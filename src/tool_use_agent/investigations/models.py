from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from tool_use_agent.tickets.models import TicketPriority


class InvestigationStatus(StrEnum):
    INVESTIGATING = "INVESTIGATING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    FAILED = "FAILED"
    APPROVED = "APPROVED"


class EvidenceKind(StrEnum):
    ATTACHMENT = "attachment"
    TOOL_RESULT = "tool_result"
    WEB_SOURCE = "web_source"
    OBSERVATION = "observation"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    APPROVED_WITH_EDITS = "approved_with_edits"
    RETURNED = "returned"


@dataclass(frozen=True)
class Investigation:
    id: int
    ticket_id: str
    session_id: str
    status: InvestigationStatus
    started_at: datetime
    diagnosed_at: datetime | None
    completed_at: datetime | None
    stop_reason: str | None
    supplemental_instructions: str | None


@dataclass(frozen=True)
class Evidence:
    id: int
    investigation_id: int
    kind: EvidenceKind
    title: str
    summary: str
    source_ref: str | None
    tool_audit_id: int | None
    attachment_id: int | None
    created_at: datetime


@dataclass(frozen=True)
class DiagnosisReport:
    id: int
    investigation_id: int
    category: str
    suggested_priority: TicketPriority
    root_cause: str
    confidence: float
    evidence_ids: tuple[int, ...]
    recommended_actions: tuple[str, ...]
    reply_draft: str
    created_at: datetime


@dataclass(frozen=True)
class Approval:
    id: int
    investigation_id: int
    decision: ApprovalDecision
    original_draft: str
    final_draft: str
    review_notes: str
    created_at: datetime


@dataclass(frozen=True)
class InvestigationEvent:
    id: int
    investigation_id: int
    event: str
    payload: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class DiagnosisTimeMetrics:
    count: int
    median_seconds: float | None
    p75_seconds: float | None
