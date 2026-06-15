import pytest

from tests.fakes import FakeAgentRunner, FakeSummarizer
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.service import ChatService


def build_service(tmp_path, *, threshold=40_000, summarizer=None):
    repository = SQLiteRepository(tmp_path / "agent.db")
    runner = FakeAgentRunner(
        answer="final answer",
        events=[
            {
                "event": "tool_start",
                "call_id": "call-1",
                "tool": "web_search",
                "arguments": {"query": "q"},
            },
            {
                "event": "tool_result",
                "call_id": "call-1",
                "tool": "web_search",
                "result": {"success": True, "data": [{"url": "a"}]},
            },
        ],
    )
    service = ChatService(
        repository=repository,
        runner=runner,
        summarizer=summarizer or FakeSummarizer(),
        context_char_threshold=threshold,
        recent_message_count=2,
    )
    return service, repository, runner


def test_chat_persists_user_assistant_tool_message_and_audit(tmp_path):
    chat_service, repository, _ = build_service(tmp_path)
    try:
        session = repository.create_session()

        result = chat_service.chat(session.id, "search and summarize")

        messages = repository.list_messages(session.id)
        assert [message.role for message in messages] == [
            "user",
            "tool",
            "assistant",
        ]
        assert result.answer == "final answer"
        audits = chat_service.list_tool_audits(session.id)
        assert audits[0].call_id == "call-1"
        assert audits[0].arguments == {"query": "q"}
    finally:
        repository.close()


def test_long_history_is_summarized_but_raw_messages_remain(tmp_path):
    summary_service, repository, _ = build_service(tmp_path, threshold=100)
    try:
        session = repository.create_session()
        for index in range(8):
            repository.add_message(
                session.id,
                "user",
                f"message-{index}-" + "x" * 50,
            )
        before = len(repository.list_messages(session.id))

        summary_service.chat(session.id, "continue")

        assert repository.get_summary(session.id).content["goals"] == [
            "continue project"
        ]
        assert len(repository.list_messages(session.id)) > before
    finally:
        repository.close()


def test_existing_summary_and_recent_messages_are_restored_as_context(tmp_path):
    service, repository, runner = build_service(tmp_path)
    try:
        session = repository.create_session()
        old = repository.add_message(session.id, "user", "old question")
        repository.save_summary(
            session.id,
            {
                "goals": ["remember this"],
                "facts": [],
                "completed_actions": [],
                "failed_attempts": [],
                "open_tasks": [],
            },
            covered_through_message_id=old.id,
        )
        repository.add_message(session.id, "assistant", "recent answer")

        service.chat(session.id, "new question")

        contents = [message.content for message in runner.invocations[0]["messages"]]
        assert "remember this" in contents[0]
        assert contents[-2:] == ["recent answer", "new question"]
    finally:
        repository.close()


def test_unknown_session_is_rejected(tmp_path):
    service, repository, _ = build_service(tmp_path)
    try:
        with pytest.raises(KeyError, match="session_not_found"):
            service.chat("missing", "hello")
    finally:
        repository.close()


def test_summary_failure_does_not_fail_answer(tmp_path):
    service, repository, _ = build_service(
        tmp_path,
        threshold=1,
        summarizer=FakeSummarizer(error=RuntimeError("provider failed")),
    )
    try:
        session = repository.create_session()
        repository.add_message(session.id, "user", "old" * 20)
        result = service.chat(session.id, "continue")

        assert result.answer == "final answer"
        assert repository.get_summary(session.id) is None
    finally:
        repository.close()


def test_stream_event_order_is_stable(tmp_path):
    service, repository, _ = build_service(tmp_path)
    try:
        session = repository.create_session()

        names = [
            event["event"]
            for event in service.stream_chat(session.id, "hello")
        ]

        assert names == [
            "message_start",
            "tool_start",
            "tool_result",
            "model_delta",
            "message_end",
        ]
    finally:
        repository.close()
