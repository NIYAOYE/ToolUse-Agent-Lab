import json

import httpx

from tool_use_agent.tools.contracts import ToolResult
from tool_use_agent.tools.registry import ToolRegistry
from tool_use_agent.tools.web_search import TavilySearchTool


class EchoTool:
    name = "echo"
    description = "Return the supplied text."
    args_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def invoke(self, arguments: dict[str, object]) -> ToolResult:
        return ToolResult(success=True, data=arguments["text"])


class BrokenTool:
    name = "broken"
    description = "Raise an unexpected exception."
    args_schema = {"type": "object", "properties": {}}

    def invoke(self, arguments: dict[str, object]) -> ToolResult:
        raise RuntimeError("internal detail")


def test_search_returns_bounded_normalized_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == "https://api.tavily.com/search"
        assert request.headers["authorization"] == "Bearer tvly-test"
        payload = json.loads(request.content)
        assert payload == {
            "query": "q",
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": False,
            "include_raw_content": False,
        }
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "A",
                        "url": "https://a.test",
                        "content": "alpha",
                        "score": 0.9,
                        "raw_content": "must not leak",
                    },
                    {
                        "title": "B",
                        "url": "https://b.test",
                        "content": "beta",
                        "score": 0.8,
                    },
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = TavilySearchTool("tvly-test", client=client).invoke(
        {"query": "q", "max_results": 99}
    )

    assert result.success is True
    assert result.data == [
        {
            "title": "A",
            "url": "https://a.test",
            "content": "alpha",
            "score": 0.9,
        },
        {
            "title": "B",
            "url": "https://b.test",
            "content": "beta",
            "score": 0.8,
        },
    ]
    assert result.metadata["result_count"] == 2


def test_search_converts_provider_failure_to_tool_error():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, json={"detail": "limited"})
        )
    )

    result = TavilySearchTool("tvly-test", client=client).invoke(
        {"query": "q"}
    )

    assert result.success is False
    assert result.error.code == "search_provider_error"
    assert "429" in result.error.message


def test_registry_returns_unknown_tool_error():
    result = ToolRegistry([EchoTool()]).invoke("missing", {})

    assert result.success is False
    assert result.error.code == "unknown_tool"


def test_registry_converts_unexpected_exception_to_safe_error():
    result = ToolRegistry([BrokenTool()]).invoke("broken", {})

    assert result.success is False
    assert result.error.code == "tool_execution_error"
    assert "internal detail" not in result.error.message


def test_registry_exposes_openai_compatible_tool_schemas():
    schemas = ToolRegistry([EchoTool()]).schemas()

    assert schemas == [
        {
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Return the supplied text.",
                "parameters": EchoTool.args_schema,
            },
        }
    ]
