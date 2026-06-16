import sys

from fastapi import FastAPI

from tool_use_agent.agent.graph import build_agent_graph
from tool_use_agent.api.app import create_app
from tool_use_agent.config import Settings
from tool_use_agent.investigations.runner import InvestigationRunner
from tool_use_agent.investigations.service import InvestigationService
from tool_use_agent.llm.qwen import AgentConfigurationError, build_qwen_model
from tool_use_agent.llm.summarizer import QwenConversationSummarizer
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.service import ChatService
from tool_use_agent.tools.file_reader import FileReaderTool
from tool_use_agent.tools.python_exec import PythonExecTool
from tool_use_agent.tools.registry import ToolRegistry
from tool_use_agent.tools.web_search import TavilySearchTool
from tool_use_agent.tickets.repository import SQLiteTicketRepository
from tool_use_agent.tickets.service import TicketService


def build_service(settings: Settings | None = None) -> ChatService:
    resolved = settings or Settings.from_env()
    repository = SQLiteRepository(resolved.database_path)
    try:
        registry, model = _build_registry_and_model(resolved)
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


def build_investigation_service(
    settings: Settings | None = None,
) -> InvestigationService:
    resolved = settings or Settings.from_env()
    memory_repository = SQLiteRepository(resolved.database_path)
    ticket_repository = SQLiteTicketRepository(resolved.database_path)
    try:
        registry, model = _build_registry_and_model(resolved)
        graph = build_agent_graph(
            model.bind_tools(registry.schemas()),
            registry,
            max_tool_steps=resolved.max_tool_steps,
        )
        return InvestigationService(
            ticket_repository=ticket_repository,
            memory_repository=memory_repository,
            runner=InvestigationRunner(
                ticket_repository=ticket_repository,
                memory_repository=memory_repository,
                agent_runner=graph,
            ),
        )
    except Exception:
        ticket_repository.close()
        memory_repository.close()
        raise


def build_ticket_service(settings: Settings | None = None) -> TicketService:
    resolved = settings or Settings.from_env()
    return TicketService(
        SQLiteTicketRepository(resolved.database_path),
        workspace_root=resolved.workspace_root,
        max_import_bytes=resolved.max_file_bytes,
        max_attachment_bytes=resolved.max_file_bytes,
        max_ticket_attachment_bytes=resolved.max_ticket_attachment_bytes,
    )


def create_application() -> FastAPI:
    settings = Settings.from_env()
    chat_service = build_service(settings)
    try:
        ticket_service = build_ticket_service(settings)
    except Exception:
        chat_service.close()
        raise
    try:
        investigation_service = build_investigation_service(settings)
    except Exception:
        ticket_service.close()
        chat_service.close()
        raise
    return create_app(
        chat_service,
        ticket_service,
        investigation_service,
        allowed_hosts=settings.allowed_hosts,
        allowed_origins=settings.allowed_origins,
    )


def _build_registry_and_model(settings: Settings):
    if not settings.tavily_api_key:
        raise AgentConfigurationError(
            "TAVILY_API_KEY is required to create the web search tool."
        )
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    registry = ToolRegistry(
        [
            TavilySearchTool(
                settings.tavily_api_key,
                timeout_seconds=settings.tool_timeout_seconds,
            ),
            FileReaderTool(
                settings.workspace_root,
                max_bytes=settings.max_file_bytes,
            ),
            PythonExecTool(
                sys.executable,
                timeout_seconds=settings.python_timeout_seconds,
                max_output_chars=settings.max_output_chars,
            ),
        ]
    )
    return registry, build_qwen_model(settings)
