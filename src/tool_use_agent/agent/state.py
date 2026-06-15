from operator import add
from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    tool_steps: int
    events: Annotated[list[dict[str, Any]], add]
    stop_reason: NotRequired[str]
