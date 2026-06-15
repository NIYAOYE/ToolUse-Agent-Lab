from collections.abc import Iterable
from typing import Any

from tool_use_agent.tools.contracts import AgentTool, ToolError, ToolResult


class ToolRegistry:
    def __init__(self, tools: Iterable[AgentTool]):
        self._tools = {tool.name: tool for tool in tools}

    def invoke(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="unknown_tool",
                    message=f"Tool '{name}' is not registered.",
                ),
            )

        try:
            return tool.invoke(arguments)
        except Exception:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="tool_execution_error",
                    message=f"Tool '{name}' failed unexpectedly.",
                ),
            )

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.args_schema,
                },
            }
            for tool in self._tools.values()
        ]
