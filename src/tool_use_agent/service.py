from dataclasses import dataclass
import json
import logging
from typing import Any, Iterator, Protocol
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from tool_use_agent.memory.models import MessageRecord
from tool_use_agent.memory.repository import SQLiteRepository


logger = logging.getLogger(__name__)

_SUMMARY_FIELDS = {
    "goals",
    "facts",
    "completed_actions",
    "failed_attempts",
    "open_tasks",
}


class AgentRunner(Protocol):
    def invoke(self, state: dict[str, Any]) -> dict[str, Any]: ...


class ConversationSummarizer(Protocol):
    def summarize(
        self,
        messages: list[MessageRecord],
        previous_summary: dict[str, Any] | None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ChatResult:
    session_id: str
    request_id: str
    answer: str
    tool_steps: int
    stop_reason: str | None
    events: list[dict[str, Any]]


class ChatService:
    def __init__(
        self,
        *,
        repository: SQLiteRepository,
        runner: AgentRunner,
        summarizer: ConversationSummarizer,
        context_char_threshold: int,
        recent_message_count: int,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._summarizer = summarizer
        self._context_char_threshold = max(1, int(context_char_threshold))
        self._recent_message_count = max(1, int(recent_message_count))

    def chat(self, session_id: str, message: str) -> ChatResult:
        events = list(self.stream_chat(session_id, message))
        completed = events[-1]
        if completed["event"] != "message_end":
            raise RuntimeError("chat_did_not_complete")
        return ChatResult(
            session_id=session_id,
            request_id=completed["request_id"],
            answer=completed["answer"],
            tool_steps=completed["tool_steps"],
            stop_reason=completed.get("stop_reason"),
            events=events,
        )

    def stream_chat(
        self,
        session_id: str,
        message: str,
    ) -> Iterator[dict[str, Any]]:
        self._repository.get_session(session_id)
        request_id = str(uuid4())
        yield {
            "event": "message_start",
            "session_id": session_id,
            "request_id": request_id,
        }

        self._repository.add_message(session_id, "user", message)
        graph_state = self._runner.invoke(
            {
                "messages": self._build_context(session_id),
                "tool_steps": 0,
                "events": [],
            }
        )

        tool_arguments: dict[str, dict[str, Any]] = {}
        for event in graph_state.get("events", []):
            enriched = {
                **event,
                "session_id": session_id,
                "request_id": request_id,
            }
            if event["event"] == "tool_start":
                tool_arguments[event["call_id"]] = event.get("arguments", {})
            elif event["event"] in {"tool_result", "tool_error"}:
                result = event.get("result", {})
                self._repository.add_tool_audit(
                    session_id,
                    event["call_id"],
                    event["tool"],
                    tool_arguments.get(event["call_id"], {}),
                    result,
                )
                self._repository.add_message(
                    session_id,
                    "tool",
                    json.dumps(result, ensure_ascii=False),
                )
            yield enriched

        answer = self._final_answer(graph_state)
        self._repository.add_message(session_id, "assistant", answer)
        yield {
            "event": "model_delta",
            "session_id": session_id,
            "request_id": request_id,
            "text": answer,
        }
        self._compact_history(session_id)
        yield {
            "event": "message_end",
            "session_id": session_id,
            "request_id": request_id,
            "answer": answer,
            "tool_steps": graph_state.get("tool_steps", 0),
            "stop_reason": graph_state.get("stop_reason"),
        }

    def create_session(self):
        return self._repository.create_session()

    def get_session(self, session_id: str):
        return self._repository.get_session(session_id)

    def list_messages(self, session_id: str):
        return self._repository.list_messages(session_id)

    def list_tool_audits(self, session_id: str):
        return self._repository.list_tool_audits(session_id)

    def close(self) -> None:
        self._repository.close()

    def _build_context(self, session_id: str) -> list[Any]:
        summary = self._repository.get_summary(session_id)
        stored_messages = self._repository.list_messages(session_id)
        context: list[Any] = []

        if summary is not None:
            context.append(
                SystemMessage(
                    content=(
                        "Conversation summary:\n"
                        + json.dumps(summary.content, ensure_ascii=False)
                    )
                )
            )
            stored_messages = [
                item
                for item in stored_messages
                if item.id > summary.covered_through_message_id
            ][-self._recent_message_count :]

        for item in stored_messages:
            if item.role == "user":
                context.append(HumanMessage(content=item.content))
            elif item.role == "assistant":
                context.append(AIMessage(content=item.content))
        return context

    @staticmethod
    def _final_answer(graph_state: dict[str, Any]) -> str:
        for message in reversed(graph_state.get("messages", [])):
            if isinstance(message, AIMessage) and message.content:
                return str(message.content)
        raise RuntimeError("agent_returned_no_answer")

    def _compact_history(self, session_id: str) -> None:
        messages = self._repository.list_messages(session_id)
        if sum(len(item.content) for item in messages) <= self._context_char_threshold:
            return
        if len(messages) <= self._recent_message_count:
            return

        older_messages = messages[: -self._recent_message_count]
        previous = self._repository.get_summary(session_id)
        try:
            content = self._summarizer.summarize(
                older_messages,
                previous.content if previous else None,
            )
            self._validate_summary(content)
            self._repository.save_summary(
                session_id,
                content,
                covered_through_message_id=older_messages[-1].id,
            )
        except Exception as exc:
            logger.warning(
                "Conversation summary failed for session %s: %s",
                session_id,
                type(exc).__name__,
            )

    @staticmethod
    def _validate_summary(content: dict[str, Any]) -> None:
        if set(content) != _SUMMARY_FIELDS:
            raise ValueError("summary_schema_mismatch")
        if any(not isinstance(content[field], list) for field in _SUMMARY_FIELDS):
            raise ValueError("summary_fields_must_be_lists")
