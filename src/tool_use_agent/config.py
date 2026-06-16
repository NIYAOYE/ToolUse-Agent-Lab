from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    dashscope_api_key: str | None
    tavily_api_key: str | None
    model_name: str
    qwen_base_url: str
    database_path: Path
    workspace_root: Path
    model_timeout_seconds: float
    tool_timeout_seconds: float
    python_timeout_seconds: float
    max_tool_steps: int
    max_file_bytes: int
    max_ticket_attachment_bytes: int
    max_output_chars: int
    context_char_threshold: int
    recent_message_count: int
    allowed_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            model_name=os.getenv("QWEN_MODEL", "qwen-plus"),
            qwen_base_url=os.getenv(
                "QWEN_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            database_path=Path(
                os.getenv("AGENT_DATABASE_PATH", "agent.db")
            ).resolve(),
            workspace_root=Path(
                os.getenv("AGENT_WORKSPACE_ROOT", "workspace")
            ).resolve(),
            model_timeout_seconds=float(
                os.getenv("AGENT_MODEL_TIMEOUT", "60")
            ),
            tool_timeout_seconds=float(
                os.getenv("AGENT_TOOL_TIMEOUT", "20")
            ),
            python_timeout_seconds=float(
                os.getenv("AGENT_PYTHON_TIMEOUT", "5")
            ),
            max_tool_steps=int(os.getenv("AGENT_MAX_TOOL_STEPS", "8")),
            max_file_bytes=int(
                os.getenv("AGENT_MAX_FILE_BYTES", "1000000")
            ),
            max_ticket_attachment_bytes=int(
                os.getenv("AGENT_MAX_TICKET_ATTACHMENT_BYTES", "5000000")
            ),
            max_output_chars=int(
                os.getenv("AGENT_MAX_OUTPUT_CHARS", "12000")
            ),
            context_char_threshold=int(
                os.getenv("AGENT_CONTEXT_CHAR_THRESHOLD", "40000")
            ),
            recent_message_count=int(
                os.getenv("AGENT_RECENT_MESSAGE_COUNT", "12")
            ),
            allowed_hosts=_csv_setting(
                "SUPPORTOPS_ALLOWED_HOSTS",
                ("127.0.0.1", "localhost", "testserver"),
            ),
            allowed_origins=_csv_setting(
                "SUPPORTOPS_ALLOWED_ORIGINS",
                (
                    "http://127.0.0.1:5173",
                    "http://localhost:5173",
                ),
            ),
        )


def _csv_setting(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    return values or default
