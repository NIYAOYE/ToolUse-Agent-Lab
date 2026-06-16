from fastapi.testclient import TestClient
import json


def ticket_payload(ticket_id="INC-1042", priority="P1"):
    return {
        "id": ticket_id,
        "title": "Database connection timeouts",
        "description": "Requests fail while acquiring a connection.",
        "environment": "production",
        "service": "orders-api",
        "priority": priority,
        "category": "runtime/database",
    }


def test_create_list_and_get_ticket(app):
    client = TestClient(app)

    created = client.post("/v1/tickets", json=ticket_payload())
    listed = client.get(
        "/v1/tickets",
        params={
            "page": 1,
            "page_size": 10,
            "priority": "P1",
            "status": "NEW",
            "sort_by": "created_at",
            "sort_order": "asc",
        },
    )
    detail = client.get("/v1/tickets/INC-1042")

    assert created.status_code == 201
    assert created.json()["id"] == "INC-1042"
    assert created.json()["source"] == "manual"
    assert created.json()["status"] == "NEW"
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["page"] == 1
    assert [item["id"] for item in listed.json()["items"]] == ["INC-1042"]
    assert detail.status_code == 200
    assert detail.json()["ticket"]["id"] == "INC-1042"
    assert detail.json()["current_investigation"] is None
    assert detail.json()["diagnosis_report"] is None


def test_duplicate_ticket_returns_stable_conflict_error(app):
    client = TestClient(app)
    client.post("/v1/tickets", json=ticket_payload())

    response = client.post("/v1/tickets", json=ticket_payload())

    assert response.status_code == 409
    assert response.json()["code"] == "ticket_already_exists"
    assert response.json()["message"] == "Ticket INC-1042 already exists."
    assert response.json()["request_id"]
    assert response.json()["details"] == {"ticket_id": "INC-1042"}


def test_missing_ticket_returns_stable_not_found_error(app):
    response = TestClient(app).get("/v1/tickets/INC-missing")

    assert response.status_code == 404
    assert response.json()["code"] == "ticket_not_found"
    assert response.json()["message"] == "Ticket INC-missing was not found."
    assert response.json()["request_id"]
    assert response.json()["details"] == {"ticket_id": "INC-missing"}


def test_delete_ticket_removes_it_from_detail_and_list(app):
    client = TestClient(app)
    client.post("/v1/tickets", json=ticket_payload())

    deleted = client.delete("/v1/tickets/INC-1042")
    detail = client.get("/v1/tickets/INC-1042")
    listed = client.get("/v1/tickets")

    assert deleted.status_code == 204
    assert detail.status_code == 404
    assert listed.status_code == 200
    assert listed.json()["total"] == 0
    assert listed.json()["items"] == []


def test_delete_missing_ticket_returns_stable_not_found_error(app):
    response = TestClient(app).delete("/v1/tickets/INC-missing")

    assert response.status_code == 404
    assert response.json()["code"] == "ticket_not_found"
    assert response.json()["message"] == "Ticket INC-missing was not found."
    assert response.json()["request_id"]
    assert response.json()["details"] == {"ticket_id": "INC-missing"}


def test_ticket_request_validation_uses_422(app):
    payload = ticket_payload()
    payload["title"] = ""

    response = TestClient(app).post("/v1/tickets", json=payload)

    assert response.status_code == 422


def test_import_json_and_csv_files(app):
    client = TestClient(app)
    json_response = client.post(
        "/v1/tickets/import",
        files={
            "file": (
                "tickets.json",
                json.dumps(
                    [
                        {
                            "id": "INC-2001",
                            "title": "JSON ticket",
                            "description": "Imported from JSON.",
                            "environment": "production",
                            "service": "orders-api",
                            "priority": "P1",
                        }
                    ]
                ),
                "application/json",
            )
        },
    )
    csv_response = client.post(
        "/v1/tickets/import",
        files={
            "file": (
                "tickets.csv",
                "id,title,description,environment,service,priority\n"
                "INC-2002,CSV ticket,Imported from CSV,staging,billing-api,P2\n",
                "text/csv",
            )
        },
    )

    assert json_response.status_code == 201
    assert json_response.json()["imported_count"] == 1
    assert json_response.json()["tickets"][0]["source"] == "json_import"
    assert csv_response.status_code == 201
    assert csv_response.json()["tickets"][0]["source"] == "csv_import"


def test_invalid_import_returns_row_errors_and_writes_nothing(app):
    response = TestClient(app).post(
        "/v1/tickets/import",
        files={
            "file": (
                "tickets.csv",
                "id,title,description,environment,service,priority\n"
                "INC-2001,,Missing title,production,orders-api,P1\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "ticket_import_validation_failed"
    assert response.json()["details"]["errors"][0]["row"] == 2
    assert TestClient(app).get("/v1/tickets").json()["total"] == 0


def test_upload_attachment_and_reject_invalid_or_oversized_file(app):
    client = TestClient(app)
    client.post("/v1/tickets", json=ticket_payload())

    uploaded = client.post(
        "/v1/tickets/INC-1042/attachments",
        files={"file": ("orders.log", b"timeout", "text/plain")},
    )
    invalid = client.post(
        "/v1/tickets/INC-1042/attachments",
        files={"file": ("run.exe", b"MZ", "application/octet-stream")},
    )
    oversized = client.post(
        "/v1/tickets/INC-1042/attachments",
        files={"file": ("large.log", b"x" * 101, "text/plain")},
    )

    assert uploaded.status_code == 201
    assert uploaded.json()["original_filename"] == "orders.log"
    assert uploaded.json()["size_bytes"] == 7
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "invalid_attachment"
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "attachment_too_large"


def test_attachment_upload_for_missing_ticket_returns_404(app):
    response = TestClient(app).post(
        "/v1/tickets/INC-missing/attachments",
        files={"file": ("orders.log", b"timeout", "text/plain")},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "ticket_not_found"
