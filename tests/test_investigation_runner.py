import json

from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage, SystemMessage
import pytest

from tests.fakes import FakeAgentRunner, ScriptedChatModel, StubTool
from tool_use_agent.agent.graph import build_agent_graph
from tool_use_agent.investigations.models import (
    EvidenceKind,
    InvestigationStatus,
)
from tool_use_agent.investigations.runner import (
    InvestigationRunError,
    InvestigationRunner,
)
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.tickets.models import TicketPriority, TicketStatus
from tool_use_agent.tickets.repository import SQLiteTicketRepository
from tool_use_agent.tools.registry import ToolRegistry


def build_investigation(tmp_path, *, answer, events):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    tickets = SQLiteTicketRepository(path)
    ticket = tickets.create_ticket(
        ticket_id="INC-1042",
        title="Database connection timeouts",
        description="Requests fail while acquiring a connection.",
        environment="production",
        service="orders-api",
        priority=TicketPriority.P1,
        category="runtime/database",
    )
    tickets.transition_status(ticket.id, TicketStatus.QUEUED)
    tickets.transition_status(ticket.id, TicketStatus.INVESTIGATING)
    attachment = tickets.add_attachment(
        ticket.id,
        original_filename="orders.log",
        stored_path="INC-1042/attachments/orders.log",
        media_type="text/plain",
        size_bytes=128,
    )
    session = memory.create_session("investigation-1")
    investigation = tickets.create_investigation(ticket.id, session.id)
    agent = FakeAgentRunner(answer=answer, events=events)
    runner = InvestigationRunner(
        ticket_repository=tickets,
        memory_repository=memory,
        agent_runner=agent,
    )
    return runner, tickets, memory, agent, investigation, attachment


def test_runner_persists_structured_report_evidence_and_context(tmp_path):
    tool_result = {
        "success": True,
        "data": [
            {
                "title": "Connection pool guide",
                "url": "https://example.com/pool-guide",
            }
        ],
    }
    answer = json.dumps(
        {
            "evidence": [
                {
                    "key": "tool-1",
                    "kind": "tool_result",
                    "title": "Search result",
                    "summary": "The search returned a relevant pool guide.",
                    "tool_call_id": "call-1",
                },
                {
                    "key": "web-1",
                    "kind": "web_source",
                    "title": "Connection pool guide",
                    "summary": "Pool exhaustion causes acquisition timeouts.",
                    "source_ref": "https://example.com/pool-guide",
                },
                {
                    "key": "attachment-1",
                    "kind": "attachment",
                    "title": "Timeout log line",
                    "summary": "The request waited 30 seconds for a connection.",
                    "source_ref": "lines 18-24",
                    "attachment_id": 1,
                },
                {
                    "key": "observation-1",
                    "kind": "observation",
                    "title": "Repeated timeout threshold",
                    "summary": "All failures use the same timeout threshold.",
                },
            ],
            "report": {
                "category": "runtime/database",
                "suggested_priority": "P1",
                "root_cause": "Database connection pool exhaustion.",
                "confidence": 0.86,
                "evidence_keys": [
                    "tool-1",
                    "web-1",
                    "attachment-1",
                    "observation-1",
                ],
                "recommended_actions": [
                    "Inspect slow queries.",
                    "Check connection leaks.",
                ],
                "reply_draft": "Initial diagnosis points to pool exhaustion.",
            },
        }
    )
    events = [
        {
            "event": "tool_start",
            "call_id": "call-1",
            "tool": "web_search",
            "arguments": {"query": "connection pool timeout"},
        },
        {
            "event": "tool_result",
            "call_id": "call-1",
            "tool": "web_search",
            "result": tool_result,
        },
    ]
    runner, tickets, memory, agent, investigation, attachment = (
        build_investigation(tmp_path, answer=answer, events=events)
    )
    try:
        result = runner.run(investigation.id)

        assert result.report.root_cause == "Database connection pool exhaustion."
        assert result.report.evidence_ids == tuple(
            evidence.id for evidence in result.evidence
        )
        assert [evidence.kind for evidence in result.evidence] == [
            EvidenceKind.TOOL_RESULT,
            EvidenceKind.WEB_SOURCE,
            EvidenceKind.ATTACHMENT,
            EvidenceKind.OBSERVATION,
        ]
        assert result.evidence[0].tool_audit_id is not None
        assert result.evidence[2].attachment_id == attachment.id
        assert memory.list_tool_audits(investigation.session_id)[0].call_id == (
            "call-1"
        )
        assert tickets.get_investigation(investigation.id).status is (
            InvestigationStatus.AWAITING_REVIEW
        )
        assert tickets.get_ticket(investigation.ticket_id).status is (
            TicketStatus.AWAITING_REVIEW
        )

        messages = agent.invocations[0]["messages"]
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)
        context = json.loads(messages[1].content)
        assert context["ticket"]["id"] == "INC-1042"
        assert context["attachments"] == [
            {
                "id": attachment.id,
                "filename": "orders.log",
                "media_type": "text/plain",
                "path": "INC-1042/attachments/orders.log",
                "size_bytes": 128,
            }
        ]
    finally:
        tickets.close()
        memory.close()


def test_runner_persists_agent_stop_reason_as_failure(tmp_path):
    runner, tickets, memory, _, investigation, _ = build_investigation(
        tmp_path,
        answer="unused",
        events=[],
    )

    class StepLimitedAgent:
        def invoke(self, state):
            return {
                **state,
                "messages": [
                    *state["messages"],
                    AIMessage(content="Tool execution stopped."),
                ],
                "stop_reason": "max_tool_steps",
            }

    runner = InvestigationRunner(
        ticket_repository=tickets,
        memory_repository=memory,
        agent_runner=StepLimitedAgent(),
    )
    try:
        with pytest.raises(InvestigationRunError) as exc_info:
            runner.run(investigation.id)

        assert exc_info.value.stop_reason == "max_tool_steps"
        failed = tickets.get_investigation(investigation.id)
        assert failed.status is InvestigationStatus.FAILED
        assert failed.stop_reason == "max_tool_steps"
        assert tickets.get_ticket(investigation.ticket_id).status is (
            TicketStatus.FAILED
        )
    finally:
        tickets.close()
        memory.close()


def test_runner_rejects_all_evidence_before_persisting_any(tmp_path):
    answer = json.dumps(
        {
            "evidence": [
                {
                    "key": "observation-1",
                    "kind": "observation",
                    "title": "Timeout pattern",
                    "summary": "Requests fail after 30 seconds.",
                },
                {
                    "key": "web-1",
                    "kind": "web_source",
                    "title": "Invented source",
                    "summary": "This URL was not returned by a tool.",
                    "source_ref": "https://example.com/not-returned",
                },
            ],
            "report": {
                "category": "runtime/database",
                "suggested_priority": "P1",
                "root_cause": "Connection pool exhaustion.",
                "confidence": 0.5,
                "evidence_keys": ["observation-1", "web-1"],
                "recommended_actions": ["Collect more evidence."],
                "reply_draft": "The current diagnosis is uncertain.",
            },
        }
    )
    runner, tickets, memory, _, investigation, _ = build_investigation(
        tmp_path,
        answer=answer,
        events=[],
    )
    try:
        with pytest.raises(InvestigationRunError) as exc_info:
            runner.run(investigation.id)

        assert exc_info.value.stop_reason == "invalid_evidence"
        assert tickets.list_evidence(investigation.id) == []
        assert tickets.get_diagnosis_report(investigation.id) is None
    finally:
        tickets.close()
        memory.close()


def test_runner_adapts_existing_graph_with_fake_model_and_tool(tmp_path):
    answer = json.dumps(
        {
            "evidence": [
                {
                    "key": "tool-1",
                    "kind": "tool_result",
                    "title": "Echo analysis",
                    "summary": "The deterministic tool returned the input.",
                    "tool_call_id": "call-1",
                }
            ],
            "report": {
                "category": "runtime/unknown",
                "suggested_priority": "P2",
                "root_cause": "The deterministic test confirms the flow.",
                "confidence": 0.6,
                "evidence_keys": ["tool-1"],
                "recommended_actions": ["Continue human investigation."],
                "reply_draft": "The structured investigation flow completed.",
            },
        }
    )
    model = ScriptedChatModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "echo",
                        "args": {"text": "inspect incident"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content=answer),
        ]
    )
    graph = build_agent_graph(
        model,
        ToolRegistry([StubTool("echo")]),
        max_tool_steps=3,
    )
    _, tickets, memory, _, investigation, _ = build_investigation(
        tmp_path,
        answer="unused",
        events=[],
    )
    runner = InvestigationRunner(
        ticket_repository=tickets,
        memory_repository=memory,
        agent_runner=graph,
    )
    try:
        result = runner.run(investigation.id)

        assert result.report.suggested_priority is TicketPriority.P2
        assert result.evidence[0].kind is EvidenceKind.TOOL_RESULT
        assert model.invocation_count == 2
        assert [event["event"] for event in result.events] == [
            "tool_start",
            "tool_result",
        ]
    finally:
        tickets.close()
        memory.close()


def test_runner_rejects_failed_tool_call_as_evidence(tmp_path):
    answer = json.dumps(
        {
            "evidence": [
                {
                    "key": "tool-1",
                    "kind": "tool_result",
                    "title": "Failed tool",
                    "summary": "This failed call must not become evidence.",
                    "tool_call_id": "call-1",
                }
            ],
            "report": {
                "category": "runtime/unknown",
                "suggested_priority": "P2",
                "root_cause": "Unsupported diagnosis.",
                "confidence": 0.2,
                "evidence_keys": ["tool-1"],
                "recommended_actions": ["Retry the investigation."],
                "reply_draft": "The tool failed.",
            },
        }
    )
    model = ScriptedChatModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "failing",
                        "args": {"text": "inspect incident"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content=answer),
        ]
    )
    graph = build_agent_graph(
        model,
        ToolRegistry([StubTool("failing", succeeds=False)]),
        max_tool_steps=3,
    )
    _, tickets, memory, _, investigation, _ = build_investigation(
        tmp_path,
        answer="unused",
        events=[],
    )
    runner = InvestigationRunner(
        ticket_repository=tickets,
        memory_repository=memory,
        agent_runner=graph,
    )
    try:
        with pytest.raises(InvestigationRunError) as exc_info:
            runner.run(investigation.id)

        assert exc_info.value.stop_reason == "invalid_evidence"
        assert tickets.list_evidence(investigation.id) == []
        assert tickets.get_diagnosis_report(investigation.id) is None
        audits = memory.list_tool_audits(investigation.session_id)
        assert len(audits) == 1
        assert audits[0].result["success"] is False
        assert tickets.get_investigation(investigation.id).status is (
            InvestigationStatus.FAILED
        )
        assert tickets.get_ticket(investigation.ticket_id).status is (
            TicketStatus.FAILED
        )
    finally:
        tickets.close()
        memory.close()


def test_runner_preserves_completed_tool_audits_at_step_limit(tmp_path):
    graph = build_agent_graph(
        ScriptedChatModel.always_calling("echo"),
        ToolRegistry([StubTool("echo")]),
        max_tool_steps=1,
    )
    _, tickets, memory, _, investigation, _ = build_investigation(
        tmp_path,
        answer="unused",
        events=[],
    )
    runner = InvestigationRunner(
        ticket_repository=tickets,
        memory_repository=memory,
        agent_runner=graph,
    )
    try:
        with pytest.raises(InvestigationRunError) as exc_info:
            runner.run(investigation.id)

        assert exc_info.value.stop_reason == "max_tool_steps"
        audits = memory.list_tool_audits(investigation.session_id)
        assert len(audits) == 1
        assert audits[0].tool_name == "echo"
        assert audits[0].result["success"] is True
    finally:
        tickets.close()
        memory.close()
