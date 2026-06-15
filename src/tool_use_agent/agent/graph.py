import json
from typing import Any, Literal, Protocol

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph

from tool_use_agent.agent.prompts import SYSTEM_PROMPT
from tool_use_agent.agent.state import AgentState
from tool_use_agent.tools.registry import ToolRegistry


class ChatModel(Protocol):
    def invoke(self, messages: list[AnyMessage]) -> AIMessage: ...


def build_agent_graph(
    model: ChatModel,
    registry: ToolRegistry,
    *,
    max_tool_steps: int,
):
    step_limit = max(1, int(max_tool_steps))

    def reason(state: AgentState) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        response = model.invoke(messages)
        return {"messages": [response]}

    def route_after_reason(
        state: AgentState,
    ) -> Literal["tools", "limit", "end"]:
        message = state["messages"][-1]
        if isinstance(message, AIMessage) and message.tool_calls:
            if state.get("tool_steps", 0) >= step_limit:
                return "limit"
            return "tools"
        return "end"

    def execute_tools(state: AgentState) -> dict[str, Any]:
        message = state["messages"][-1]
        if not isinstance(message, AIMessage):
            raise TypeError("tools node requires an AIMessage")

        tool_messages: list[ToolMessage] = []
        events: list[dict[str, Any]] = []
        for call in message.tool_calls:
            call_id = call["id"]
            name = call["name"]
            arguments = call.get("args", {})
            events.append(
                {
                    "event": "tool_start",
                    "call_id": call_id,
                    "tool": name,
                    "arguments": arguments,
                }
            )
            result = registry.invoke(name, arguments)
            serialized = result.to_dict()
            events.append(
                {
                    "event": "tool_result" if result.success else "tool_error",
                    "call_id": call_id,
                    "tool": name,
                    "result": serialized,
                }
            )
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(serialized, ensure_ascii=False),
                    tool_call_id=call_id,
                    name=name,
                )
            )
        return {
            "messages": tool_messages,
            "tool_steps": state.get("tool_steps", 0) + 1,
            "events": events,
        }

    def stop_at_limit(state: AgentState) -> dict[str, Any]:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "Tool execution stopped after reaching the configured "
                        "step limit."
                    )
                )
            ],
            "stop_reason": "max_tool_steps",
        }

    builder = StateGraph(AgentState)
    builder.add_node("reason", reason)
    builder.add_node("tools", execute_tools)
    builder.add_node("limit", stop_at_limit)
    builder.add_edge(START, "reason")
    builder.add_conditional_edges(
        "reason",
        route_after_reason,
        {"tools": "tools", "limit": "limit", "end": END},
    )
    builder.add_edge("tools", "reason")
    builder.add_edge("limit", END)
    return builder.compile()
