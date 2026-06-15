import os
import re
from dataclasses import replace

from langchain_core.messages import HumanMessage
import pytest

from tool_use_agent.composition import build_service
from tool_use_agent.config import Settings
from tool_use_agent.llm.qwen import build_qwen_model
from tool_use_agent.tools.web_search import TavilySearchTool


pytestmark = pytest.mark.live


def _require_live_keys() -> None:
    if not os.getenv("DASHSCOPE_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        pytest.skip("DASHSCOPE_API_KEY and TAVILY_API_KEY are required")


def test_live_qwen_returns_a_short_answer():
    _require_live_keys()
    model = build_qwen_model(Settings.from_env())

    response = model.invoke(
        [HumanMessage(content="Reply with exactly: QWEN_OK")]
    )

    assert "QWEN_OK" in str(response.content)


def test_live_tavily_returns_normalized_results():
    _require_live_keys()
    settings = Settings.from_env()
    result = TavilySearchTool(
        settings.tavily_api_key,
        timeout_seconds=settings.tool_timeout_seconds,
    ).invoke({"query": "LangGraph official documentation", "max_results": 2})

    assert result.success is True
    assert result.data
    assert set(result.data[0]) == {"title", "url", "content", "score"}


def test_live_agent_uses_web_search_and_returns_source_url(tmp_path):
    _require_live_keys()
    settings = Settings.from_env()
    settings = replace(
        settings,
        database_path=tmp_path / "live-agent.db",
        workspace_root=tmp_path / "workspace",
    )
    service = build_service(settings)
    try:
        session = service.create_session()
        result = service.chat(
            session.id,
            (
                "Use web_search to find the official LangGraph documentation. "
                "Return one concise sentence and include a full source URL."
            ),
        )
        audits = service.list_tool_audits(session.id)

        assert any(item.tool_name == "web_search" for item in audits)
        assert re.search(r"https?://\S+", result.answer)
    finally:
        service.close()
