import pytest

from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.investigations.models import (
    ApprovalDecision,
    EvidenceKind,
)
from tool_use_agent.tickets.models import TicketPriority
from tool_use_agent.tickets.repository import (
    ActiveInvestigationExists,
    InvalidDiagnosisReport,
    InvalidEvidenceReference,
    SQLiteTicketRepository,
)


def create_ticket(repo, ticket_id="INC-1042"):
    return repo.create_ticket(
        ticket_id=ticket_id,
        title="Database connection timeouts",
        description="Requests fail while acquiring a connection.",
        environment="production",
        service="orders-api",
        priority=TicketPriority.P1,
    )


def test_attachment_and_investigation_survive_repository_restart(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    session = memory.create_session("session-1")
    first = SQLiteTicketRepository(path)
    ticket = create_ticket(first)
    attachment = first.add_attachment(
        ticket.id,
        original_filename="orders.log",
        stored_path="INC-1042/attachments/orders.log",
        media_type="text/plain",
        size_bytes=128,
    )
    investigation = first.create_investigation(ticket.id, session.id)
    first.close()
    memory.close()

    second = SQLiteTicketRepository(path)
    try:
        assert second.list_attachments(ticket.id) == [attachment]
        assert second.get_investigation(investigation.id) == investigation
        assert investigation.ticket_id == ticket.id
        assert investigation.session_id == session.id
        assert investigation.started_at.tzinfo is not None
        assert investigation.diagnosed_at is None
        assert investigation.completed_at is None
    finally:
        second.close()


def test_investigation_requires_existing_ticket_and_session(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    memory.create_session("session-1")
    repo = SQLiteTicketRepository(path)
    ticket = create_ticket(repo)
    try:
        with pytest.raises(KeyError, match="ticket_not_found"):
            repo.create_investigation("INC-missing", "session-1")

        with pytest.raises(KeyError, match="session_not_found"):
            repo.create_investigation(ticket.id, "session-missing")
    finally:
        repo.close()
        memory.close()


def test_ticket_can_have_only_one_active_investigation(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    memory.create_session("session-1")
    memory.create_session("session-2")
    repo = SQLiteTicketRepository(path)
    ticket = create_ticket(repo)
    try:
        repo.create_investigation(ticket.id, "session-1")

        with pytest.raises(ActiveInvestigationExists) as exc_info:
            repo.create_investigation(ticket.id, "session-2")

        assert exc_info.value.code == "active_investigation_exists"
        assert exc_info.value.ticket_id == ticket.id
    finally:
        repo.close()
        memory.close()


def test_evidence_references_are_validated_and_restored(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    session = memory.create_session("session-1")
    audit = memory.add_tool_audit(
        session.id,
        "call-1",
        "web_search",
        {"query": "connection pool timeout"},
        {"success": True},
    )
    repo = SQLiteTicketRepository(path)
    ticket = create_ticket(repo)
    attachment = repo.add_attachment(
        ticket.id,
        original_filename="orders.log",
        stored_path="INC-1042/attachments/orders.log",
        media_type="text/plain",
        size_bytes=128,
    )
    investigation = repo.create_investigation(ticket.id, session.id)
    tool = repo.add_evidence(
        investigation.id,
        kind=EvidenceKind.TOOL_RESULT,
        title="Search result",
        summary="Provider documentation describes pool exhaustion.",
        tool_audit_id=audit.id,
    )
    web = repo.add_evidence(
        investigation.id,
        kind=EvidenceKind.WEB_SOURCE,
        title="Database pool guide",
        summary="Connections wait when the pool is exhausted.",
        source_ref="https://example.com/pool-guide",
    )
    attached = repo.add_evidence(
        investigation.id,
        kind=EvidenceKind.ATTACHMENT,
        title="Timeout log line",
        summary="The request waited 30 seconds for a connection.",
        source_ref="lines 18-24",
        attachment_id=attachment.id,
    )
    observation = repo.add_evidence(
        investigation.id,
        kind=EvidenceKind.OBSERVATION,
        title="Repeated timing",
        summary="All failures use the same timeout threshold.",
    )
    repo.close()
    memory.close()

    restored = SQLiteTicketRepository(path)
    try:
        assert restored.list_evidence(investigation.id) == [
            tool,
            web,
            attached,
            observation,
        ]
    finally:
        restored.close()


def test_invalid_evidence_reference_is_rejected(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    session = memory.create_session("session-1")
    repo = SQLiteTicketRepository(path)
    ticket = create_ticket(repo)
    investigation = repo.create_investigation(ticket.id, session.id)
    try:
        with pytest.raises(InvalidEvidenceReference) as exc_info:
            repo.add_evidence(
                investigation.id,
                kind=EvidenceKind.WEB_SOURCE,
                title="Bad source",
                summary="Missing URL.",
                source_ref="not-a-url",
            )

        assert exc_info.value.code == "invalid_evidence_reference"
        assert repo.list_evidence(investigation.id) == []
    finally:
        repo.close()
        memory.close()


def test_tool_evidence_must_use_audit_from_investigation_session(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    memory.create_session("session-1")
    memory.create_session("session-2")
    audit = memory.add_tool_audit(
        "session-2",
        "call-1",
        "web_search",
        {"query": "q"},
        {"success": True},
    )
    repo = SQLiteTicketRepository(path)
    ticket = create_ticket(repo)
    investigation = repo.create_investigation(ticket.id, "session-1")
    try:
        with pytest.raises(InvalidEvidenceReference):
            repo.add_evidence(
                investigation.id,
                kind=EvidenceKind.TOOL_RESULT,
                title="Wrong session",
                summary="Audit belongs to another session.",
                tool_audit_id=audit.id,
            )

        assert repo.list_evidence(investigation.id) == []
    finally:
        repo.close()
        memory.close()


def test_attachment_evidence_must_use_attachment_from_investigation_ticket(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    memory.create_session("session-1")
    repo = SQLiteTicketRepository(path)
    first = create_ticket(repo, "INC-1042")
    second = create_ticket(repo, "INC-1043")
    attachment = repo.add_attachment(
        second.id,
        original_filename="other.log",
        stored_path="INC-1043/attachments/other.log",
        media_type="text/plain",
        size_bytes=64,
    )
    investigation = repo.create_investigation(first.id, "session-1")
    try:
        with pytest.raises(InvalidEvidenceReference):
            repo.add_evidence(
                investigation.id,
                kind=EvidenceKind.ATTACHMENT,
                title="Wrong attachment",
                summary="Attachment belongs to another ticket.",
                source_ref="lines 1-2",
                attachment_id=attachment.id,
            )

        assert repo.list_evidence(investigation.id) == []
    finally:
        repo.close()
        memory.close()


def test_diagnosis_report_rejects_evidence_from_another_investigation(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    memory.create_session("session-1")
    memory.create_session("session-2")
    repo = SQLiteTicketRepository(path)
    first = create_ticket(repo, "INC-1042")
    second = create_ticket(repo, "INC-1043")
    first_investigation = repo.create_investigation(first.id, "session-1")
    second_investigation = repo.create_investigation(second.id, "session-2")
    first_evidence = repo.add_evidence(
        first_investigation.id,
        kind=EvidenceKind.OBSERVATION,
        title="First observation",
        summary="Belongs to the first investigation.",
    )
    second_evidence = repo.add_evidence(
        second_investigation.id,
        kind=EvidenceKind.OBSERVATION,
        title="Second observation",
        summary="Belongs to the second investigation.",
    )
    try:
        with pytest.raises(InvalidDiagnosisReport) as exc_info:
            repo.save_diagnosis_report(
                first_investigation.id,
                category="runtime/database",
                suggested_priority=TicketPriority.P1,
                root_cause="Connection pool exhaustion.",
                confidence=0.86,
                evidence_ids=[first_evidence.id, second_evidence.id],
                recommended_actions=["Inspect slow queries."],
                reply_draft="Initial diagnosis.",
            )

        assert exc_info.value.code == "invalid_diagnosis_report"
        assert repo.get_diagnosis_report(first_investigation.id) is None
    finally:
        repo.close()
        memory.close()


def test_diagnosis_report_rejects_confidence_outside_unit_interval(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    memory.create_session("session-1")
    repo = SQLiteTicketRepository(path)
    ticket = create_ticket(repo)
    investigation = repo.create_investigation(ticket.id, "session-1")
    try:
        with pytest.raises(InvalidDiagnosisReport):
            repo.save_diagnosis_report(
                investigation.id,
                category="runtime/database",
                suggested_priority=TicketPriority.P1,
                root_cause="Unknown.",
                confidence=1.1,
                evidence_ids=[],
                recommended_actions=["Collect more evidence."],
                reply_draft="More investigation is required.",
            )

        assert repo.get_diagnosis_report(investigation.id) is None
    finally:
        repo.close()
        memory.close()


def test_diagnosis_and_approval_history_survive_restart(tmp_path):
    path = tmp_path / "agent.db"
    memory = SQLiteRepository(path)
    memory.create_session("session-1")
    repo = SQLiteTicketRepository(path)
    ticket = create_ticket(repo)
    investigation = repo.create_investigation(ticket.id, "session-1")
    evidence = repo.add_evidence(
        investigation.id,
        kind=EvidenceKind.OBSERVATION,
        title="Timeout pattern",
        summary="Failures consistently wait 30 seconds.",
    )
    report = repo.save_diagnosis_report(
        investigation.id,
        category="runtime/database",
        suggested_priority=TicketPriority.P1,
        root_cause="Connection pool exhaustion.",
        confidence=0.86,
        evidence_ids=[evidence.id],
        recommended_actions=["Inspect slow queries.", "Check connection leaks."],
        reply_draft="Initial diagnosis.",
    )
    returned = repo.add_approval(
        investigation.id,
        decision=ApprovalDecision.RETURNED,
        original_draft=report.reply_draft,
        final_draft=report.reply_draft,
        review_notes="Check the latest deployment first.",
    )
    approved = repo.add_approval(
        investigation.id,
        decision=ApprovalDecision.APPROVED_WITH_EDITS,
        original_draft=report.reply_draft,
        final_draft="Edited and approved diagnosis.",
        review_notes="Added deployment context.",
    )
    repo.close()
    memory.close()

    restored = SQLiteTicketRepository(path)
    try:
        assert restored.get_diagnosis_report(investigation.id) == report
        assert report.evidence_ids == (evidence.id,)
        assert report.recommended_actions == (
            "Inspect slow queries.",
            "Check connection leaks.",
        )
        assert restored.list_approvals(investigation.id) == [returned, approved]
    finally:
        restored.close()
