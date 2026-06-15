from collections import deque
from typing import Any

from langchain_core.messages import AIMessage

from tool_use_agent.tools.contracts import ToolError, ToolResult


class ScriptedChatModel:
    def __init__(self, responses: list[AIMessage]):
        self._responses = deque(responses)
        self.invocations: list[list[Any]] = []

    @property
    def invocation_count(self) -> int:
        return len(self.invocations)

    def invoke(self, messages: list[Any]) -> AIMessage:
        self.invocations.append(list(messages))
        if not self._responses:
            raise AssertionError("No scripted model response remains.")
        return self._responses.popleft()

    @classmethod
    def always_calling(cls, tool_name: str) -> "AlwaysCallingChatModel":
        return AlwaysCallingChatModel(tool_name)


class AlwaysCallingChatModel(ScriptedChatModel):
    def __init__(self, tool_name: str):
        super().__init__([])
        self._tool_name = tool_name

    def invoke(self, messages: list[Any]) -> AIMessage:
        self.invocations.append(list(messages))
        call_number = len(self.invocations)
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": self._tool_name,
                    "args": {"text": "hi"},
                    "id": f"call-{call_number}",
                    "type": "tool_call",
                }
            ],
        )


class StubTool:
    description = "A deterministic test tool."
    args_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
    }

    def __init__(self, name: str, *, succeeds: bool = True):
        self.name = name
        self._succeeds = succeeds

    def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        if self._succeeds:
            return ToolResult(success=True, data=arguments)
        return ToolResult(
            success=False,
            error=ToolError(code="stub_failure", message="Stub tool failed."),
        )


class FakeAgentRunner:
    def __init__(self, *, answer: str, events: list[dict[str, Any]]):
        self.answer = answer
        self.events = events
        self.invocations: list[dict[str, Any]] = []

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        self.invocations.append(state)
        return {
            **state,
            "messages": [*state["messages"], AIMessage(content=self.answer)],
            "events": list(self.events),
            "tool_steps": sum(
                event["event"] == "tool_result" for event in self.events
            ),
        }


class FakeSummarizer:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.invocations: list[tuple[list[Any], dict[str, Any] | None]] = []

    def summarize(
        self,
        messages: list[Any],
        previous_summary: dict[str, Any] | None,
    ) -> dict[str, Any]:
        self.invocations.append((messages, previous_summary))
        if self.error:
            raise self.error
        return {
            "goals": ["continue project"],
            "facts": [],
            "completed_actions": [],
            "failed_attempts": [],
            "open_tasks": [],
        }
