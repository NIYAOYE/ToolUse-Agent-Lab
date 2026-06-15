from time import perf_counter
from typing import Any

import httpx

from tool_use_agent.tools.contracts import ToolError, ToolResult


class TavilySearchTool:
    name = "web_search"
    description = "Search the web for up-to-date information using Tavily."
    args_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return, from 1 to 5.",
                "minimum": 1,
                "maximum": 5,
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 20,
    ):
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        started_at = perf_counter()
        query = str(arguments.get("query", "")).strip()
        max_results = self._bounded_result_count(arguments.get("max_results", 5))

        if not query:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="invalid_search_query",
                    message="Search query must not be empty.",
                ),
            )

        try:
            response = self._client.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score"),
                }
                for item in payload.get("results", [])[:max_results]
            ]
        except httpx.HTTPStatusError as exc:
            return self._provider_error(
                f"Tavily search failed with HTTP {exc.response.status_code}.",
                started_at,
            )
        except (httpx.HTTPError, TypeError, ValueError, AttributeError):
            return self._provider_error(
                "Tavily search request failed.",
                started_at,
            )

        return ToolResult(
            success=True,
            data=results,
            metadata={
                "duration_ms": self._duration_ms(started_at),
                "result_count": len(results),
            },
        )

    @staticmethod
    def _bounded_result_count(value: Any) -> int:
        try:
            result_count = int(value)
        except (TypeError, ValueError):
            result_count = 5
        return min(5, max(1, result_count))

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

    def _provider_error(
        self,
        message: str,
        started_at: float,
    ) -> ToolResult:
        return ToolResult(
            success=False,
            error=ToolError(
                code="search_provider_error",
                message=message,
            ),
            metadata={"duration_ms": self._duration_ms(started_at)},
        )
