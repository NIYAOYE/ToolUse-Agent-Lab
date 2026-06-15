import sys

from fastapi import FastAPI

from tool_use_agent.agent.graph import build_agent_graph
from tool_use_agent.api.app import create_app
from tool_use_agent.config import Settings
from tool_use_agent.llm.qwen import AgentConfigurationError, build_qwen_model
from tool_use_agent.llm.summarizer import QwenConversationSummarizer
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.service import ChatService
from tool_use_agent.tools.file_reader import FileReaderTool
from tool_use_agent.tools.python_exec import PythonExecTool
from tool_use_agent.tools.registry import ToolRegistry
from tool_use_agent.tools.web_search import TavilySearchTool


def build_service(settings: Settings | None = None) -> ChatService:
    resolved = settings or Settings.from_env()
    if not resolved.tavily_api_key:
        raise AgentConfigurationError(
            "TAVILY_API_KEY is required to create the web search tool."
        )

    resolved.workspace_root.mkdir(parents=True, exist_ok=True)
    repository = SQLiteRepository(resolved.database_path)
    try:
        registry = ToolRegistry(
            [
                TavilySearchTool(
                    resolved.tavily_api_key,
                    timeout_seconds=resolved.tool_timeout_seconds,
                ),
                FileReaderTool(
                    resolved.workspace_root,
                    max_bytes=resolved.max_file_bytes,
                ),
                PythonExecTool(
                    sys.executable,
                    timeout_seconds=resolved.python_timeout_seconds,
                    max_output_chars=resolved.max_output_chars,
                ),
            ]
        )
        model = build_qwen_model(resolved)
        runner = build_agent_graph(
            model.bind_tools(registry.schemas()),
            registry,
            max_tool_steps=resolved.max_tool_steps,
        )
        return ChatService(
            repository=repository,
            runner=runner,
            summarizer=QwenConversationSummarizer(model),
            context_char_threshold=resolved.context_char_threshold,
            recent_message_count=resolved.recent_message_count,
        )
    except Exception:
        repository.close()
        raise


def create_application() -> FastAPI:
    return create_app(build_service())
