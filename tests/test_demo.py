from fastapi.testclient import TestClient

from tests.fakes import FakeAgentRunner, FakeSummarizer
from tool_use_agent.api.app import create_app
from tool_use_agent.demo import seed_demo_tickets
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.service import ChatService
from tool_use_agent.tickets.repository import SQLiteTicketRepository
from tool_use_agent.tickets.service import TicketService


def test_demo_seed_is_deterministic_idempotent_and_does_not_start_work(tmp_path):
    repository = SQLiteTicketRepository(tmp_path / "demo.db")
    service = TicketService(repository, workspace_root=tmp_path / "workspace")
    try:
        first = seed_demo_tickets(service)
        second = seed_demo_tickets(service)
        page = service.list_tickets(page=1, page_size=20)

        assert first.created == 4
        assert first.existing == 0
        assert second.created == 0
        assert second.existing == 4
        assert sorted(ticket.id for ticket in page.items) == [
            "DEMO-1001",
            "DEMO-1002",
            "DEMO-1003",
            "DEMO-1004",
        ]
        assert {ticket.status.value for ticket in page.items} == {"NEW"}
    finally:
        service.close()


def test_seeded_demo_tickets_are_available_through_the_http_api(tmp_path):
    database_path = tmp_path / "demo-api.db"
    memory = SQLiteRepository(database_path)
    tickets = SQLiteTicketRepository(database_path)
    chat = ChatService(
        repository=memory,
        runner=FakeAgentRunner(answer="unused", events=[]),
        summarizer=FakeSummarizer(),
        context_char_threshold=40_000,
        recent_message_count=12,
    )
    service = TicketService(tickets, workspace_root=tmp_path / "workspace")
    try:
        seed_demo_tickets(service)
        response = TestClient(create_app(chat, service)).get(
            "/v1/tickets",
            params={"page_size": 20},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 4
        assert {item["id"] for item in response.json()["items"]} == {
            "DEMO-1001",
            "DEMO-1002",
            "DEMO-1003",
            "DEMO-1004",
        }
    finally:
        service.close()
        chat.close()
