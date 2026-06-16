import json
import logging

from fastapi.testclient import TestClient

from tests.fakes import FakeAgentRunner, FakeSummarizer
from tool_use_agent.api.app import _REQUEST_LOGGER, _request_id, create_app
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.service import ChatService


def test_health_reports_ready(app):
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_requests_emit_json_log_and_response_request_id(app, caplog):
    assert _REQUEST_LOGGER.name == (
        "uvicorn.error.tool_use_agent.api.requests"
    )
    with caplog.at_level(logging.INFO, logger=_REQUEST_LOGGER.name):
        response = TestClient(app).get(
            "/health?api_key=do-not-log",
            headers={"X-Request-ID": "supportops-request_42"},
        )

    record = json.loads(caplog.records[-1].message)
    assert response.headers["x-request-id"] == "supportops-request_42"
    assert record["request_id"] == "supportops-request_42"
    assert record["method"] == "GET"
    assert record["path"] == "/health"
    assert record["status_code"] == 200
    assert record["duration_ms"] >= 0
    assert "query" not in record
    assert "body" not in record
    assert "do-not-log" not in caplog.records[-1].message


def test_unicode_request_id_is_replaced(app):
    assert _request_id("请求-42") != "请求-42"


def test_default_host_and_cors_boundaries(app):
    allowed_get = TestClient(app).get(
        "/health",
        headers={"Origin": "http://127.0.0.1:5173"},
    )
    allowed = TestClient(app).options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    disallowed_origin = TestClient(app).options(
        "/health",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    disallowed_host = TestClient(
        app,
        base_url="http://evil.example",
    ).get("/health")

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:5173"
    )
    assert allowed_get.headers["access-control-expose-headers"] == (
        "X-Request-ID"
    )
    assert "access-control-allow-origin" not in disallowed_origin.headers
    assert disallowed_host.status_code == 400


def test_create_session_chat_and_read_history(app):
    client = TestClient(app)
    session_response = client.post("/v1/sessions")
    session_id = session_response.json()["id"]

    response = client.post(
        "/v1/chat",
        json={"session_id": session_id, "message": "hello"},
    )
    session = client.get(f"/v1/sessions/{session_id}")
    history = client.get(f"/v1/sessions/{session_id}/messages")

    assert session_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["answer"] == "final answer"
    assert response.json()["tool_steps"] == 1
    assert session.json()["id"] == session_id
    assert [item["role"] for item in history.json()] == [
        "user",
        "tool",
        "assistant",
    ]


def test_stream_emits_named_events_in_order(app):
    client = TestClient(app)
    session_id = client.post("/v1/sessions").json()["id"]

    with client.stream(
        "POST",
        "/v1/chat/stream",
        json={"session_id": session_id, "message": "use tool"},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert body.index("event: message_start") < body.index("event: tool_start")
    assert body.index("event: tool_start") < body.index("event: tool_result")
    assert body.index("event: tool_result") < body.index("event: message_end")


def test_unknown_session_returns_404_for_chat_and_stream(app):
    client = TestClient(app)

    chat = client.post(
        "/v1/chat",
        json={"session_id": "missing", "message": "hello"},
    )
    stream = client.post(
        "/v1/chat/stream",
        json={"session_id": "missing", "message": "hello"},
    )

    assert chat.status_code == 404
    assert chat.json()["detail"] == "session_not_found"
    assert stream.status_code == 404


def test_empty_message_returns_validation_error(app):
    client = TestClient(app)
    session_id = client.post("/v1/sessions").json()["id"]

    response = client.post(
        "/v1/chat",
        json={"session_id": session_id, "message": ""},
    )

    assert response.status_code == 422


def test_stream_encodes_tool_error_event(tmp_path):
    repository = SQLiteRepository(tmp_path / "error.db")
    try:
        runner = FakeAgentRunner(
            answer="could not search",
            events=[
                {
                    "event": "tool_start",
                    "call_id": "call-error",
                    "tool": "web_search",
                    "arguments": {"query": "q"},
                },
                {
                    "event": "tool_error",
                    "call_id": "call-error",
                    "tool": "web_search",
                    "result": {
                        "success": False,
                        "error": {"code": "search_provider_error"},
                    },
                },
            ],
        )
        service = ChatService(
            repository=repository,
            runner=runner,
            summarizer=FakeSummarizer(),
            context_char_threshold=40_000,
            recent_message_count=12,
        )
        client = TestClient(create_app(service))
        session_id = client.post("/v1/sessions").json()["id"]

        response = client.post(
            "/v1/chat/stream",
            json={"session_id": session_id, "message": "search"},
        )

        assert "event: tool_error" in response.text
        assert "search_provider_error" in response.text
    finally:
        repository.close()
