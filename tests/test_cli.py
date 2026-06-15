import httpx

from tool_use_agent.cli import run_chat


def test_cli_creates_session_and_prints_stream_events(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/sessions":
            return httpx.Response(201, json={"id": "session-1"})
        assert request.url.path == "/v1/chat/stream"
        return httpx.Response(
            200,
            text=(
                'event: tool_start\ndata: {"tool":"web_search"}\n\n'
                'event: tool_result\ndata: {"tool":"web_search"}\n\n'
                'event: message_end\ndata: {"answer":"hello"}\n\n'
            ),
            headers={"content-type": "text/event-stream"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
    )

    run_chat(client, session_id=None, input_lines=iter(["question", "/quit"]))

    output = capsys.readouterr().out
    assert "session-1" in output
    assert "web_search" in output
    assert "hello" in output


def test_cli_resumes_supplied_session_without_creating_one(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path != "/v1/sessions"
        return httpx.Response(
            200,
            text='event: message_end\ndata: {"answer":"ok"}\n\n',
            headers={"content-type": "text/event-stream"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
    )

    run_chat(
        client,
        session_id="existing",
        input_lines=iter(["hello", "/quit"]),
    )

    output = capsys.readouterr().out
    assert "existing" in output
    assert "ok" in output


def test_cli_prints_tool_errors_without_stopping_session(capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                'event: tool_error\ndata: {"tool":"web_search",'
                '"result":{"error":{"code":"search_provider_error"}}}\n\n'
                'event: message_end\ndata: {"answer":"fallback"}\n\n'
            ),
            headers={"content-type": "text/event-stream"},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
    )

    run_chat(
        client,
        session_id="existing",
        input_lines=iter(["hello", "/quit"]),
    )

    output = capsys.readouterr().out
    assert "search_provider_error" in output
    assert "fallback" in output
