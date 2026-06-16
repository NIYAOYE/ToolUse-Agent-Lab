import json

from fastapi.testclient import TestClient

from tests.fakes import FakeAgentRunner, FakeSummarizer
from tool_use_agent.api.app import create_app
from tool_use_agent.investigations.runner import InvestigationRunner
from tool_use_agent.investigations.service import InvestigationService
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.service import ChatService
from tool_use_agent.tickets.repository import SQLiteTicketRepository
from tool_use_agent.tickets.service import TicketService


def ticket_payload():
    return {
        "id": "INC-1042",
        "title": "Database connection timeouts",
        "description": "Requests fail while acquiring a connection.",
        "environment": "production",
        "service": "orders-api",
        "priority": "P1",
        "category": "runtime/database",
    }


def diagnosis_answer():
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
                "root_cause": "Connection pool exhaustion.",
                "confidence": 0.8,
                "evidence_keys": ["observation-1"],
                "recommended_actions": ["Inspect slow queries."],
                "reply_draft": "Initial diagnosis points to pool exhaustion.",
            },
        }
    )


def build_app(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    tickets = SQLiteTicketRepository(path)
    chat = ChatService(
        repository=memory,
        runner=FakeAgentRunner(answer="final answer", events=[]),
        summarizer=FakeSummarizer(),
        context_char_threshold=40_000,
        recent_message_count=12,
    )
    ticket_service = TicketService(
        tickets,
        workspace_root=tmp_path / "workspace",
        max_import_bytes=1000,
        max_attachment_bytes=100,
        max_ticket_attachment_bytes=200,
    )
    runner = InvestigationRunner(
        ticket_repository=tickets,
        memory_repository=memory,
        agent_runner=FakeAgentRunner(answer=diagnosis_answer(), events=[]),
    )
    investigations = InvestigationService(
        ticket_repository=tickets,
        memory_repository=memory,
        runner=runner,
    )
    app = create_app(chat, ticket_service, investigations)
    return app, tickets, memory


def test_start_detail_and_sse_resume(tmp_path):
    app, tickets, memory = build_app(tmp_path)
    client = TestClient(app)
    try:
        client.post("/v1/tickets", json=ticket_payload())

        started = client.post("/v1/tickets/INC-1042/investigations")
        investigation_id = started.json()["id"]
        detail = client.get(f"/v1/investigations/{investigation_id}")
        events = detail.json()["events"]
        stream = client.get(f"/v1/investigations/{investigation_id}/events")
        resumed = client.get(
            f"/v1/investigations/{investigation_id}/events",
            params={"after_id": events[0]["id"]},
        )

        assert started.status_code == 202
        assert detail.status_code == 200
        assert detail.json()["investigation"]["status"] == "AWAITING_REVIEW"
        assert detail.json()["report"]["root_cause"] == (
            "Connection pool exhaustion."
        )
        assert stream.headers["content-type"].startswith("text/event-stream")
        assert "event: investigation_started" in stream.text
        assert "event: diagnosis_ready" in stream.text
        assert "event: investigation_started" not in resumed.text
        assert "event: diagnosis_ready" in resumed.text
    finally:
        tickets.close()
        memory.close()


def test_start_conflict_and_missing_investigation_errors(tmp_path):
    app, tickets, memory = build_app(tmp_path)
    client = TestClient(app)
    try:
        client.post("/v1/tickets", json=ticket_payload())
        client.post("/v1/tickets/INC-1042/investigations")

        conflict = client.post("/v1/tickets/INC-1042/investigations")
        missing = client.get("/v1/investigations/999")

        assert conflict.status_code == 409
        assert conflict.json()["code"] == "active_investigation_exists"
        assert missing.status_code == 404
        assert missing.json()["code"] == "investigation_not_found"
    finally:
        tickets.close()
        memory.close()


def test_return_reruns_then_approve_with_edits(tmp_path):
    app, tickets, memory = build_app(tmp_path)
    client = TestClient(app)
    try:
        client.post("/v1/tickets", json=ticket_payload())
        investigation_id = client.post(
            "/v1/tickets/INC-1042/investigations"
        ).json()["id"]

        returned = client.post(
            f"/v1/investigations/{investigation_id}/decision",
            json={
                "decision": "returned",
                "review_notes": "Check the latest deployment.",
            },
        )
        approved = client.post(
            f"/v1/investigations/{investigation_id}/decision",
            json={
                "decision": "approved_with_edits",
                "final_draft": "Edited and approved diagnosis.",
                "review_notes": "Added deployment context.",
            },
        )
        detail = client.get(f"/v1/investigations/{investigation_id}")

        assert returned.status_code == 200
        assert returned.json()["should_run"] is True
        assert approved.status_code == 200
        assert approved.json()["investigation"]["status"] == "APPROVED"
        assert [item["decision"] for item in detail.json()["approvals"]] == [
            "returned",
            "approved_with_edits",
        ]
    finally:
        tickets.close()
        memory.close()


def test_diagnosis_time_metrics_api(tmp_path):
    app, tickets, memory = build_app(tmp_path)
    client = TestClient(app)
    try:
        client.post("/v1/tickets", json=ticket_payload())
        client.post("/v1/tickets/INC-1042/investigations")

        response = client.get("/v1/metrics/diagnosis-time")

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["median_seconds"] >= 0
        assert response.json()["p75_seconds"] >= 0
    finally:
        tickets.close()
        memory.close()
