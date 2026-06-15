from dataclasses import replace

from langchain_core.messages import AIMessage
import pytest

from tests.fakes import ScriptedChatModel, StubTool
from tool_use_agent.agent.graph import build_agent_graph
from tool_use_agent.config import Settings
from tool_use_agent.llm import qwen as qwen_module
from tool_use_agent.llm.qwen import AgentConfigurationError, build_qwen_model
from tool_use_agent.tools.registry import ToolRegistry


def test_graph_executes_tool_and_returns_final_answer():
    model = ScriptedChatModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "echo",
                        "args": {"text": "hi"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    graph = build_agent_graph(
        model,
        ToolRegistry([StubTool("echo")]),
        max_tool_steps=3,
    )

    state = graph.invoke({"messages": [], "tool_steps": 0, "events": []})

    assert state["messages"][-1].content == "done"
    assert state["tool_steps"] == 1
    assert model.invocation_count == 2
    assert [event["event"] for event in state["events"]] == [
        "tool_start",
        "tool_result",
    ]


def test_graph_returns_controlled_error_at_step_limit():
    model = ScriptedChatModel.always_calling("echo")
    graph = build_agent_graph(
        model,
        ToolRegistry([StubTool("echo")]),
        max_tool_steps=2,
    )

    state = graph.invoke({"messages": [], "tool_steps": 0, "events": []})

    assert state["stop_reason"] == "max_tool_steps"
    assert state["tool_steps"] == 2
    assert state["messages"][-1].content.startswith("Tool execution stopped")


def test_graph_returns_failed_tool_result_to_model():
    model = ScriptedChatModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "failing",
                        "args": {},
                        "id": "call-2",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="The tool failed, so I could not complete it."),
        ]
    )
    graph = build_agent_graph(
        model,
        ToolRegistry([StubTool("failing", succeeds=False)]),
        max_tool_steps=3,
    )

    state = graph.invoke({"messages": [], "tool_steps": 0, "events": []})

    assert state["messages"][-1].content.startswith("The tool failed")
    assert '"success": false' in model.invocations[1][-1].content
    assert state["events"][-1]["event"] == "tool_error"


def test_qwen_builder_requires_dashscope_api_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    settings = replace(Settings.from_env(), dashscope_api_key=None)

    with pytest.raises(AgentConfigurationError, match="DASHSCOPE_API_KEY"):
        build_qwen_model(settings)


def test_qwen_builder_uses_configured_openai_compatible_values(monkeypatch):
    captured: dict[str, object] = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(qwen_module, "ChatOpenAI", FakeChatOpenAI)
    settings = replace(
        Settings.from_env(),
        dashscope_api_key="dash-test",
        model_name="qwen-plus",
        qwen_base_url="https://dashscope.test/v1",
        model_timeout_seconds=12,
    )

    model = build_qwen_model(settings)

    assert isinstance(model, FakeChatOpenAI)
    assert captured == {
        "model": "qwen-plus",
        "api_key": "dash-test",
        "base_url": "https://dashscope.test/v1",
        "temperature": 0,
        "timeout": 12,
        "max_retries": 2,
    }
