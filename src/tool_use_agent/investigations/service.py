from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from tool_use_agent.investigations.models import (
    Approval,
    ApprovalDecision,
    DiagnosisReport,
    DiagnosisTimeMetrics,
    Evidence,
    Investigation,
    InvestigationEvent,
    InvestigationStatus,
)
from tool_use_agent.investigations.runner import (
    InvestigationRunError,
    InvestigationRunner,
)
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.tickets.models import TicketStatus
from tool_use_agent.tickets.repository import (
    ActiveInvestigationExists,
    SQLiteTicketRepository,
)


class InvalidInvestigationState(ValueError):
    code = "invalid_investigation_state"

    def __init__(self, status: InvestigationStatus):
        self.status = status
        super().__init__(f"Investigation is not reviewable from {status}.")


class InvalidApprovalDecision(ValueError):
    code = "invalid_approval_decision"


@dataclass(frozen=True)
class InvestigationDetail:
    investigation: Investigation
    evidence: tuple[Evidence, ...]
    report: DiagnosisReport | None
    approvals: tuple[Approval, ...]
    events: tuple[InvestigationEvent, ...]


@dataclass(frozen=True)
class DecisionOutcome:
    investigation: Investigation
    approvals: tuple[Approval, ...]
    should_run: bool


class InvestigationService:
    def __init__(
        self,
        *,
        ticket_repository: SQLiteTicketRepository,
        memory_repository: SQLiteRepository,
        runner: InvestigationRunner,
    ) -> None:
        self._tickets = ticket_repository
        self._memory = memory_repository
        self._runner = runner
        self._lock = RLock()

    def start(
        self,
        ticket_id: str,
        *,
        supplemental_instructions: str | None = None,
    ) -> Investigation:
        with self._lock:
            ticket = self._tickets.get_ticket(ticket_id)
            current = self._tickets.get_current_investigation(ticket_id)
            if current is not None:
                if current.status is not InvestigationStatus.FAILED:
                    raise ActiveInvestigationExists(ticket_id)
                investigation = self._tickets.mark_investigation_investigating(
                    current.id,
                    supplemental_instructions=supplemental_instructions,
                )
                self._tickets.transition_status(
                    ticket_id,
                    TicketStatus.INVESTIGATING,
                )
                self._tickets.add_investigation_event(
                    investigation.id,
                    "investigation_retried",
                    {
                        "ticket_id": ticket_id,
                        "supplemental_instructions": supplemental_instructions,
                    },
                )
                return investigation

            if ticket.status not in {TicketStatus.NEW, TicketStatus.QUEUED}:
                raise ActiveInvestigationExists(ticket_id)
            session = self._memory.create_session()
            investigation = self._tickets.create_investigation(
                ticket_id,
                session.id,
            )
            if supplemental_instructions:
                investigation = self._tickets.mark_investigation_investigating(
                    investigation.id,
                    supplemental_instructions=supplemental_instructions,
                )
            if ticket.status is TicketStatus.NEW:
                self._tickets.transition_status(ticket_id, TicketStatus.QUEUED)
                self._tickets.transition_status(
                    ticket_id,
                    TicketStatus.INVESTIGATING,
                )
            elif ticket.status is TicketStatus.QUEUED:
                self._tickets.transition_status(
                    ticket_id,
                    TicketStatus.INVESTIGATING,
                )
            self._tickets.add_investigation_event(
                investigation.id,
                "investigation_started",
                {"ticket_id": ticket_id},
            )
            return investigation

    def run(self, investigation_id: int) -> InvestigationDetail:
        try:
            result = self._runner.run(investigation_id)
        except InvestigationRunError as exc:
            self._tickets.add_investigation_event(
                investigation_id,
                "investigation_failed",
                {"stop_reason": exc.stop_reason},
            )
            return self.get_detail(investigation_id)

        for event in result.events:
            name = str(event.get("event", "investigation_event"))
            self._tickets.add_investigation_event(
                investigation_id,
                name,
                self._public_tool_event(event),
            )
        self._tickets.add_investigation_event(
            investigation_id,
            "diagnosis_ready",
            {
                "report_id": result.report.id,
                "confidence": result.report.confidence,
            },
        )
        return self.get_detail(investigation_id)

    def get_detail(self, investigation_id: int) -> InvestigationDetail:
        return InvestigationDetail(
            investigation=self._tickets.get_investigation(investigation_id),
            evidence=tuple(self._tickets.list_evidence(investigation_id)),
            report=self._tickets.get_diagnosis_report(investigation_id),
            approvals=tuple(self._tickets.list_approvals(investigation_id)),
            events=tuple(
                self._tickets.list_investigation_events(investigation_id)
            ),
        )

    def list_events(
        self,
        investigation_id: int,
        *,
        after_id: int = 0,
    ) -> list[InvestigationEvent]:
        return self._tickets.list_investigation_events(
            investigation_id,
            after_id=after_id,
        )

    def decide(
        self,
        investigation_id: int,
        *,
        decision: ApprovalDecision,
        final_draft: str | None = None,
        review_notes: str = "",
    ) -> DecisionOutcome:
        with self._lock:
            investigation = self._tickets.get_investigation(investigation_id)
            if investigation.status is not InvestigationStatus.AWAITING_REVIEW:
                raise InvalidInvestigationState(investigation.status)
            report = self._tickets.get_diagnosis_report(investigation_id)
            if report is None:
                raise InvalidApprovalDecision("diagnosis report is missing")
            if decision is ApprovalDecision.APPROVED_WITH_EDITS:
                if not final_draft or not final_draft.strip():
                    raise InvalidApprovalDecision(
                        "edited approval requires a final draft"
                    )
                resolved_draft = final_draft.strip()
            else:
                resolved_draft = report.reply_draft
            self._tickets.add_approval(
                investigation_id,
                decision=decision,
                original_draft=report.reply_draft,
                final_draft=resolved_draft,
                review_notes=review_notes,
            )

            if decision is ApprovalDecision.RETURNED:
                updated = self._tickets.mark_investigation_investigating(
                    investigation_id,
                    supplemental_instructions=review_notes or None,
                )
                self._tickets.transition_status(
                    investigation.ticket_id,
                    TicketStatus.INVESTIGATING,
                )
                self._tickets.add_investigation_event(
                    investigation_id,
                    "investigation_returned",
                    {"review_notes": review_notes},
                )
                should_run = True
            else:
                updated = self._tickets.mark_investigation_approved(
                    investigation_id
                )
                self._tickets.transition_status(
                    investigation.ticket_id,
                    TicketStatus.APPROVED,
                )
                self._tickets.add_investigation_event(
                    investigation_id,
                    "investigation_approved",
                    {"decision": decision.value},
                )
                should_run = False
            return DecisionOutcome(
                investigation=updated,
                approvals=tuple(self._tickets.list_approvals(investigation_id)),
                should_run=should_run,
            )

    def get_diagnosis_time_metrics(self) -> DiagnosisTimeMetrics:
        return self._tickets.get_diagnosis_time_metrics()

    def close(self) -> None:
        self._tickets.close()
        self._memory.close()

    @staticmethod
    def _public_tool_event(event: dict[str, object]) -> dict[str, object]:
        payload: dict[str, object] = {
            "call_id": event.get("call_id"),
            "tool": event.get("tool"),
        }
        if event.get("event") in {"tool_result", "tool_error"}:
            result = event.get("result")
            if isinstance(result, dict):
                payload["success"] = bool(result.get("success"))
                error = result.get("error")
                if isinstance(error, dict) and error.get("code"):
                    payload["error_code"] = error["code"]
        return payload
