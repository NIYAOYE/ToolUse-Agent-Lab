from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolError:
    code: str
    message: str


@dataclass(frozen=True)
class ToolResult:
    success: bool
    data: Any = None
    error: ToolError | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentTool(Protocol):
    name: str
    description: str
    args_schema: dict[str, Any]

    def invoke(self, arguments: dict[str, Any]) -> ToolResult: ...
