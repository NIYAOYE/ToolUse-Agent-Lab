from collections import deque
import json

from langchain_core.messages import AIMessage
import pytest

from tool_use_agent.investigations.models import (
    ApprovalDecision,
    InvestigationStatus,
)
from tool_use_agent.investigations.runner import InvestigationRunner
from tool_use_agent.investigations.service import (
    InvestigationService,
    InvalidInvestigationState,
)
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.tickets.models import TicketPriority, TicketStatus
from tool_use_agent.tickets.repository import (
    ActiveInvestigationExists,
    SQLiteTicketRepository,
)


def diagnosis_answer(root_cause="Connection pool exhaustion."):
    return json.dumps(
        {
            "evidence": [
                {
                    "key": "observation-1",
                    "kind": "observation",
                    "title": "Timeout pattern",
                    "summary": "Requests consistently time out after 30 seconds.",
                }
            ],
            "report": {
                "category": "runtime/database",
                "suggested_priority": "P1",
                "root_cause": root_cause,
                "confidence": 0.8,
                "evidence_keys": ["observation-1"],
                "recommended_actions": ["Inspect slow queries."],
                "reply_draft": "Initial diagnosis points to pool exhaustion.",
            },
        }
    )


class SequenceAgent:
    def __init__(self, answers):
        self.answers = deque(answers)

    def invoke(self, state):
        answer = self.answers.popleft()
        return {
            **state,
            "messages": [*state["messages"], AIMessage(content=answer)],
            "events": [],
            "tool_steps": 0,
        }


def build_service(tmp_path, answers=None):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    tickets = SQLiteTicketRepository(path)
    ticket = tickets.create_ticket(
        ticket_id="INC-1042",
        title="Database timeouts",
        description="Requests time out.",
        environment="production",
        service="orders-api",
        priority=TicketPriority.P1,
    )
    runner = InvestigationRunner(
        ticket_repository=tickets,
        memory_repository=memory,
        agent_runner=SequenceAgent(answers or [diagnosis_answer()]),
    )
    service = InvestigationService(
        ticket_repository=tickets,
        memory_repository=memory,
        runner=runner,
    )
    return service, tickets, memory, ticket


def test_start_and_run_investigation_persists_recoverable_events(tmp_path):
    service, tickets, memory, ticket = build_service(tmp_path)
    try:
        investigation = service.start(ticket.id)
        detail = service.run(investigation.id)

        assert tickets.get_ticket(ticket.id).status is TicketStatus.AWAITING_REVIEW
        assert detail.investigation.status is InvestigationStatus.AWAITING_REVIEW
        assert detail.report is not None
        assert [event.event for event in detail.events] == [
            "investigation_started",
            "diagnosis_ready",
        ]
        assert service.list_events(
            investigation.id,
            after_id=detail.events[0].id,
        ) == [detail.events[1]]
    finally:
        tickets.close()
        memory.close()


def test_duplicate_start_returns_active_investigation_conflict(tmp_path):
    service, tickets, memory, ticket = build_service(tmp_path)
    try:
        service.start(ticket.id)

        with pytest.raises(ActiveInvestigationExists):
            service.start(ticket.id)
    finally:
        tickets.close()
        memory.close()


def test_failed_investigation_retries_same_context(tmp_path):
    service, tickets, memory, ticket = build_service(
        tmp_path,
        answers=["not-json", diagnosis_answer("Deployment regression.")],
    )
    try:
        investigation = service.start(ticket.id)
        failed = service.run(investigation.id)
        retried = service.start(
            ticket.id,
            supplemental_instructions="Check the latest deployment.",
        )
        diagnosed = service.run(retried.id)

        assert failed.investigation.status is InvestigationStatus.FAILED
        assert retried.id == investigation.id
        assert retried.supplemental_instructions == (
            "Check the latest deployment."
        )
        assert diagnosed.report.root_cause == "Deployment regression."
        assert [event.event for event in diagnosed.events] == [
            "investigation_started",
            "investigation_failed",
            "investigation_retried",
            "diagnosis_ready",
        ]
    finally:
        tickets.close()
        memory.close()


def test_return_then_approve_with_edits_keeps_approval_history(tmp_path):
    service, tickets, memory, ticket = build_service(
        tmp_path,
        answers=[diagnosis_answer(), diagnosis_answer("Deployment regression.")],
    )
    try:
        investigation = service.start(ticket.id)
        service.run(investigation.id)

        returned = service.decide(
            investigation.id,
            decision=ApprovalDecision.RETURNED,
            review_notes="Check the latest deployment.",
        )
        service.run(investigation.id)
        approved = service.decide(
            investigation.id,
            decision=ApprovalDecision.APPROVED_WITH_EDITS,
            final_draft="Edited and approved diagnosis.",
            review_notes="Added deployment context.",
        )

        assert returned.should_run is True
        assert approved.should_run is False
        assert approved.investigation.status is InvestigationStatus.APPROVED
        assert tickets.get_ticket(ticket.id).status is TicketStatus.APPROVED
        assert [item.decision for item in approved.approvals] == [
            ApprovalDecision.RETURNED,
            ApprovalDecision.APPROVED_WITH_EDITS,
        ]
        with pytest.raises(InvalidInvestigationState):
            service.decide(
                investigation.id,
                decision=ApprovalDecision.APPROVED,
                review_notes="Already complete.",
            )
    finally:
        tickets.close()
        memory.close()


def test_approved_ticket_rejects_restart_without_creating_investigation(
    tmp_path,
):
    service, tickets, memory, ticket = build_service(tmp_path)
    try:
        investigation = service.start(ticket.id)
        service.run(investigation.id)
        service.decide(
            investigation.id,
            decision=ApprovalDecision.APPROVED,
            review_notes="Approved.",
        )

        with pytest.raises(ActiveInvestigationExists):
            service.start(ticket.id)

        assert tickets.get_current_investigation(ticket.id) is None
    finally:
        tickets.close()
        memory.close()
