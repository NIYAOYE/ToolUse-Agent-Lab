from datetime import datetime, timezone
import sqlite3

from tool_use_agent.investigations.models import InvestigationStatus
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.tickets.models import TicketPriority
from tool_use_agent.tickets.repository import SQLiteTicketRepository


def build_investigation(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    memory.create_session("session-1")
    repo = SQLiteTicketRepository(path)
    ticket = repo.create_ticket(
        ticket_id="INC-1042",
        title="Database timeouts",
        description="Requests time out.",
        environment="production",
        service="orders-api",
        priority=TicketPriority.P1,
    )
    investigation = repo.create_investigation(ticket.id, "session-1")
    return path, memory, repo, investigation


def test_investigation_events_survive_restart_and_support_resume(tmp_path):
    path, memory, repo, investigation = build_investigation(tmp_path)
    first = repo.add_investigation_event(
        investigation.id,
        "investigation_started",
        {"ticket_id": investigation.ticket_id},
    )
    second = repo.add_investigation_event(
        investigation.id,
        "tool_result",
        {"tool": "web_search", "success": True},
    )
    repo.close()

    restored = SQLiteTicketRepository(path)
    try:
        assert restored.list_investigation_events(investigation.id) == [
            first,
            second,
        ]
        assert restored.list_investigation_events(
            investigation.id,
            after_id=first.id,
        ) == [second]
    finally:
        restored.close()
        memory.close()


def test_retry_preserves_first_diagnosis_time_and_approval_completes(tmp_path):
    _, memory, repo, investigation = build_investigation(tmp_path)
    try:
        diagnosed = repo.mark_investigation_awaiting_review(investigation.id)
        retried = repo.mark_investigation_investigating(
            investigation.id,
            supplemental_instructions="Check the latest deployment.",
        )
        diagnosed_again = repo.mark_investigation_awaiting_review(
            investigation.id
        )
        approved = repo.mark_investigation_approved(investigation.id)

        assert retried.status is InvestigationStatus.INVESTIGATING
        assert retried.supplemental_instructions == (
            "Check the latest deployment."
        )
        assert diagnosed_again.diagnosed_at == diagnosed.diagnosed_at
        assert approved.status is InvestigationStatus.APPROVED
        assert approved.completed_at is not None
    finally:
        repo.close()
        memory.close()


def test_diagnosis_time_metrics_return_median_and_p75(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    repo = SQLiteTicketRepository(path)
    try:
        for index, seconds in enumerate((10, 20, 30, 40), start=1):
            session_id = f"session-{index}"
            ticket_id = f"INC-{index}"
            memory.create_session(session_id)
            repo.create_ticket(
                ticket_id=ticket_id,
                title="Timeout",
                description="Request timeout.",
                environment="production",
                service="orders-api",
                priority=TicketPriority.P1,
            )
            investigation = repo.create_investigation(ticket_id, session_id)
            started = datetime(2026, 1, 1, tzinfo=timezone.utc)
            diagnosed = datetime.fromtimestamp(
                started.timestamp() + seconds,
                tz=timezone.utc,
            )
            with sqlite3.connect(path) as connection:
                connection.execute(
                    """
                    UPDATE investigations
                    SET diagnosed_at = ?, status = ?
                    WHERE id = ?
                    """,
                    (
                        diagnosed.isoformat(),
                        InvestigationStatus.AWAITING_REVIEW.value,
                        investigation.id,
                    ),
                )
                connection.execute(
                    "UPDATE investigations SET started_at = ? WHERE id = ?",
                    (started.isoformat(), investigation.id),
                )

        metrics = repo.get_diagnosis_time_metrics()

        assert metrics.count == 4
        assert metrics.median_seconds == 25
        assert metrics.p75_seconds == 32.5
    finally:
        repo.close()
        memory.close()
