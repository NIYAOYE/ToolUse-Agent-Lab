from pathlib import Path

from tool_use_agent.config import Settings


def test_settings_read_required_keys_from_environment(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash-test")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(tmp_path / "files"))

    settings = Settings.from_env()

    assert settings.dashscope_api_key == "dash-test"
    assert settings.tavily_api_key == "tvly-test"
    assert settings.model_name == "qwen-plus"
    assert settings.workspace_root == (tmp_path / "files").resolve()


def test_settings_use_china_openai_compatible_endpoint(monkeypatch):
    monkeypatch.delenv("QWEN_BASE_URL", raising=False)

    settings = Settings.from_env()

    assert (
        settings.qwen_base_url
        == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
