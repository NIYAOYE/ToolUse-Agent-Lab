from dataclasses import replace
from datetime import datetime, timezone

from langchain_core.messages import AIMessage
import pytest

from tests.fakes import ScriptedChatModel
from tool_use_agent.composition import (
    build_investigation_service,
    build_service,
)
from tool_use_agent.config import Settings
from tool_use_agent.llm.qwen import AgentConfigurationError
from tool_use_agent.llm.summarizer import QwenConversationSummarizer
from tool_use_agent.memory.models import MessageRecord
from tool_use_agent.tickets.models import TicketPriority
from tool_use_agent.tickets.repository import SQLiteTicketRepository


def test_qwen_summarizer_parses_fenced_json_and_includes_previous_summary():
    model = ScriptedChatModel(
        [
            AIMessage(
                content=(
                    "```json\n"
                    '{"goals":["ship"],"facts":[],"completed_actions":[],'
                    '"failed_attempts":[],"open_tasks":["test"]}'
                    "\n```"
                )
            )
        ]
    )
    summarizer = QwenConversationSummarizer(model)
    message = MessageRecord(
        id=1,
        session_id="session",
        role="user",
        content="continue",
        created_at=datetime.now(timezone.utc),
    )

    result = summarizer.summarize([message], {"goals": ["previous"]})

    assert result["goals"] == ["ship"]
    prompt = model.invocations[0][-1].content
    assert "previous" in prompt
    assert "continue" in prompt


def test_build_service_wires_three_tools_and_creates_workspace(
    monkeypatch,
    tmp_path,
):
    captured: dict[str, object] = {}

    class FakeBindableModel:
        def bind_tools(self, schemas):
            captured["schemas"] = schemas
            return ScriptedChatModel([AIMessage(content="done")])

        def invoke(self, messages):
            return AIMessage(content="{}")

    monkeypatch.setattr(
        "tool_use_agent.composition.build_qwen_model",
        lambda settings: FakeBindableModel(),
    )
    settings = replace(
        Settings.from_env(),
        dashscope_api_key="dash-test",
        tavily_api_key="tvly-test",
        database_path=tmp_path / "agent.db",
        workspace_root=tmp_path / "workspace",
    )

    service = build_service(settings)
    try:
        session = service.create_session()
        assert session.id
        assert settings.workspace_root.exists()
        assert [
            schema["function"]["name"] for schema in captured["schemas"]
        ] == ["web_search", "read_file", "python_exec"]
    finally:
        service.close()


def test_build_service_requires_tavily_api_key(tmp_path):
    settings = replace(
        Settings.from_env(),
        dashscope_api_key="dash-test",
        tavily_api_key=None,
        database_path=tmp_path / "agent.db",
        workspace_root=tmp_path / "workspace",
    )

    with pytest.raises(AgentConfigurationError, match="TAVILY_API_KEY"):
        build_service(settings)


def test_build_investigation_service_uses_real_database_and_tools(
    monkeypatch,
    tmp_path,
):
    captured: dict[str, object] = {}

    class FakeBindableModel:
        def bind_tools(self, schemas):
            captured["schemas"] = schemas
            return ScriptedChatModel([AIMessage(content="unused")])

    monkeypatch.setattr(
        "tool_use_agent.composition.build_qwen_model",
        lambda settings: FakeBindableModel(),
    )
    settings = replace(
        Settings.from_env(),
        dashscope_api_key="dash-test",
        tavily_api_key="tvly-test",
        database_path=tmp_path / "agent.db",
        workspace_root=tmp_path / "workspace",
    )
    repository = SQLiteTicketRepository(settings.database_path)
    repository.create_ticket(
        ticket_id="INC-1042",
        title="Timeout",
        description="Request timeout.",
        environment="production",
        service="orders-api",
        priority=TicketPriority.P1,
    )
    repository.close()

    service = build_investigation_service(settings)
    try:
        investigation = service.start("INC-1042")

        assert investigation.ticket_id == "INC-1042"
        assert [
            schema["function"]["name"] for schema in captured["schemas"]
        ] == ["web_search", "read_file", "python_exec"]
    finally:
        service.close()
