from langchain_openai import ChatOpenAI

from tool_use_agent.config import Settings


class AgentConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing."""


def build_qwen_model(settings: Settings) -> ChatOpenAI:
    if not settings.dashscope_api_key:
        raise AgentConfigurationError(
            "DASHSCOPE_API_KEY is required to create the Qwen model."
        )
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.dashscope_api_key,
        base_url=settings.qwen_base_url,
        temperature=0,
        timeout=settings.model_timeout_seconds,
        max_retries=2,
    )
