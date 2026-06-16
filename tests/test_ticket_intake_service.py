import json

import pytest

from tool_use_agent.tickets.models import TicketPriority, TicketSource
from tool_use_agent.tickets.repository import SQLiteTicketRepository
from tool_use_agent.tickets.service import (
    AttachmentTooLarge,
    AttachmentValidationError,
    TicketImportTooLarge,
    TicketImportValidationError,
    TicketService,
)


def build_service(tmp_path, *, max_bytes=100, max_ticket_bytes=200):
    repository = SQLiteTicketRepository(tmp_path / "agent.db")
    service = TicketService(
        repository,
        workspace_root=tmp_path / "workspace",
        max_attachment_bytes=max_bytes,
        max_ticket_attachment_bytes=max_ticket_bytes,
    )
    return repository, service


def create_ticket(service, ticket_id="INC-1042"):
    return service.create_ticket(
        ticket_id=ticket_id,
        title="Database connection timeouts",
        description="Requests fail.",
        environment="production",
        service="orders-api",
        priority=TicketPriority.P1,
    )


def test_json_import_creates_all_tickets_with_json_source(tmp_path):
    repository, service = build_service(tmp_path)
    payload = json.dumps(
        [
            {
                "id": "INC-1001",
                "title": "First failure",
                "description": "First description",
                "environment": "production",
                "service": "orders-api",
                "priority": "P1",
            },
            {
                "id": "INC-1002",
                "title": "Second failure",
                "description": "Second description",
                "environment": "staging",
                "service": "billing-api",
                "priority": "P2",
                "category": "runtime/dependency",
            },
        ]
    ).encode()
    try:
        imported = service.import_tickets("tickets.json", payload)

        assert [item.id for item in imported] == ["INC-1001", "INC-1002"]
        assert all(item.source is TicketSource.JSON_IMPORT for item in imported)
    finally:
        repository.close()


def test_csv_import_validation_is_atomic(tmp_path):
    repository, service = build_service(tmp_path)
    payload = (
        "id,title,description,environment,service,priority\n"
        "INC-1001,Valid,Works,production,orders-api,P1\n"
        "INC-1002,,Missing title,production,orders-api,P2\n"
    ).encode()
    try:
        with pytest.raises(TicketImportValidationError) as exc_info:
            service.import_tickets("tickets.csv", payload)

        assert exc_info.value.code == "ticket_import_validation_failed"
        assert exc_info.value.errors[0]["row"] == 3
        assert exc_info.value.errors[0]["field"] == "title"
        assert repository.list_tickets(offset=0, limit=20)[1] == 0
    finally:
        repository.close()


def test_import_rejects_duplicate_ids_without_partial_write(tmp_path):
    repository, service = build_service(tmp_path)
    payload = json.dumps(
        [
            {
                "id": "INC-1001",
                "title": "First",
                "description": "Description",
                "environment": "production",
                "service": "orders-api",
                "priority": "P1",
            },
            {
                "id": "INC-1001",
                "title": "Duplicate",
                "description": "Description",
                "environment": "production",
                "service": "orders-api",
                "priority": "P1",
            },
        ]
    ).encode()
    try:
        with pytest.raises(TicketImportValidationError):
            service.import_tickets("tickets.json", payload)

        assert repository.list_tickets(offset=0, limit=20)[1] == 0
    finally:
        repository.close()


def test_csv_import_rejects_missing_required_columns_without_rows(tmp_path):
    repository, service = build_service(tmp_path)
    try:
        with pytest.raises(TicketImportValidationError) as exc_info:
            service.import_tickets("tickets.csv", b"id,title\n")

        assert {error["field"] for error in exc_info.value.errors} >= {
            "description",
            "environment",
            "service",
            "priority",
        }
    finally:
        repository.close()


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("tickets.json", b"[]"),
        (
            "tickets.csv",
            b"id,title,description,environment,service,priority\n",
        ),
    ],
)
def test_import_rejects_empty_batch(tmp_path, filename, content):
    repository, service = build_service(tmp_path)
    try:
        with pytest.raises(TicketImportValidationError) as exc_info:
            service.import_tickets(filename, content)

        assert exc_info.value.errors == [
            {"row": 0, "field": "file", "message": "Import is empty."}
        ]
    finally:
        repository.close()


def test_import_rejects_oversized_file(tmp_path):
    repository = SQLiteTicketRepository(tmp_path / "agent.db")
    service = TicketService(
        repository,
        workspace_root=tmp_path / "workspace",
        max_import_bytes=2,
    )
    try:
        with pytest.raises(TicketImportTooLarge):
            service.import_tickets("tickets.json", b"[{}]")
    finally:
        repository.close()


def test_attachment_is_written_inside_isolated_ticket_directory(tmp_path):
    repository, service = build_service(tmp_path)
    ticket = create_ticket(service)
    try:
        attachment = service.save_attachment(
            ticket.id,
            filename="orders.log",
            media_type="text/plain",
            content=b"timeout while acquiring connection",
        )

        stored = tmp_path / "workspace" / attachment.stored_path
        assert stored.read_bytes() == b"timeout while acquiring connection"
        assert attachment.original_filename == "orders.log"
        assert attachment.ticket_id == ticket.id
        assert ".." not in attachment.stored_path
    finally:
        repository.close()


def test_delete_ticket_removes_attachment_files(tmp_path):
    repository, service = build_service(tmp_path)
    ticket = create_ticket(service)
    try:
        attachment = service.save_attachment(
            ticket.id,
            filename="orders.log",
            media_type="text/plain",
            content=b"timeout while acquiring connection",
        )
        stored = tmp_path / "workspace" / attachment.stored_path

        service.delete_ticket(ticket.id)

        assert not stored.exists()
        with pytest.raises(KeyError):
            repository.get_ticket(ticket.id)
    finally:
        repository.close()


def test_attachment_rejects_forbidden_type_and_oversized_content(tmp_path):
    repository, service = build_service(tmp_path, max_bytes=4)
    ticket = create_ticket(service)
    try:
        with pytest.raises(AttachmentValidationError) as type_error:
            service.save_attachment(
                ticket.id,
                filename="run.exe",
                media_type="application/octet-stream",
                content=b"MZ",
            )
        assert type_error.value.code == "invalid_attachment"

        with pytest.raises(AttachmentTooLarge) as size_error:
            service.save_attachment(
                ticket.id,
                filename="orders.log",
                media_type="text/plain",
                content=b"12345",
            )
        assert size_error.value.code == "attachment_too_large"
        assert repository.list_attachments(ticket.id) == []
    finally:
        repository.close()


def test_json_attachment_rejects_content_that_is_not_json(tmp_path):
    repository, service = build_service(tmp_path)
    ticket = create_ticket(service)
    try:
        with pytest.raises(AttachmentValidationError):
            service.save_attachment(
                ticket.id,
                filename="payload.json",
                media_type="application/json",
                content=b"not json",
            )

        assert repository.list_attachments(ticket.id) == []
    finally:
        repository.close()


def test_attachment_rejects_ticket_total_size_over_limit(tmp_path):
    repository, service = build_service(
        tmp_path,
        max_bytes=10,
        max_ticket_bytes=10,
    )
    ticket = create_ticket(service)
    try:
        service.save_attachment(
            ticket.id,
            filename="first.log",
            media_type="text/plain",
            content=b"123456",
        )

        with pytest.raises(AttachmentTooLarge):
            service.save_attachment(
                ticket.id,
                filename="second.log",
                media_type="text/plain",
                content=b"78901",
            )

        assert len(repository.list_attachments(ticket.id)) == 1
    finally:
        repository.close()
