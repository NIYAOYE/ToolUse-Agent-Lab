import json
from typing import Any, Protocol

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage

from tool_use_agent.memory.models import MessageRecord


class SummaryModel(Protocol):
    def invoke(self, messages: list[AnyMessage]) -> AIMessage: ...


class QwenConversationSummarizer:
    def __init__(self, model: SummaryModel) -> None:
        self._model = model

    def summarize(
        self,
        messages: list[MessageRecord],
        previous_summary: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = {
            "previous_summary": previous_summary,
            "messages": [
                {"role": item.role, "content": item.content}
                for item in messages
            ],
        }
        response = self._model.invoke(
            [
                SystemMessage(
                    content=(
                        "Summarize the conversation as JSON with exactly these "
                        "list fields: goals, facts, completed_actions, "
                        "failed_attempts, open_tasks. Return JSON only."
                    )
                ),
                HumanMessage(
                    content=json.dumps(payload, ensure_ascii=False)
                ),
            ]
        )
        if not isinstance(response.content, str):
            raise ValueError("summary_response_must_be_text")
        return json.loads(self._strip_code_fence(response.content))

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        stripped = content.strip()
        if not stripped.startswith("```"):
            return stripped
        lines = stripped.splitlines()
        if len(lines) < 3 or lines[-1].strip() != "```":
            raise ValueError("invalid_summary_code_fence")
        return "\n".join(lines[1:-1]).strip()
