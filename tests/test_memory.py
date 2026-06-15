import pytest

from tool_use_agent.memory.repository import SQLiteRepository


def test_session_messages_survive_repository_restart(tmp_path):
    path = tmp_path / "agent.db"
    first = SQLiteRepository(path)
    session = first.create_session()
    message = first.add_message(session.id, "user", "hello")
    first.close()

    second = SQLiteRepository(path)
    try:
        restored = second.get_session(session.id)
        messages = second.list_messages(session.id)
        assert restored.id == session.id
        assert [(item.id, item.role, item.content) for item in messages] == [
            (message.id, "user", "hello")
        ]
    finally:
        second.close()


def test_tool_audits_keep_call_order_and_restore_json(tmp_path):
    repo = SQLiteRepository(tmp_path / "agent.db")
    try:
        session = repo.create_session()
        repo.add_tool_audit(
            session.id,
            "call-1",
            "web_search",
            {"query": "q"},
            {"success": True, "data": [1]},
        )
        repo.add_tool_audit(
            session.id,
            "call-2",
            "read_file",
            {"path": "a.txt"},
            {"success": False, "error": {"code": "missing"}},
        )

        audits = repo.list_tool_audits(session.id)

        assert [row.call_id for row in audits] == ["call-1", "call-2"]
        assert audits[0].arguments == {"query": "q"}
        assert audits[0].result == {"success": True, "data": [1]}
    finally:
        repo.close()


def test_summary_is_replaced_without_deleting_raw_messages(tmp_path):
    repo = SQLiteRepository(tmp_path / "agent.db")
    try:
        session = repo.create_session()
        message = repo.add_message(session.id, "user", "keep me")
        repo.save_summary(
            session.id,
            {"goals": ["first"]},
            covered_through_message_id=message.id,
        )
        repo.save_summary(
            session.id,
            {"goals": ["second"]},
            covered_through_message_id=message.id,
        )

        summary = repo.get_summary(session.id)

        assert summary.content["goals"] == ["second"]
        assert summary.covered_through_message_id == message.id
        assert repo.list_messages(session.id)[0].content == "keep me"
    finally:
        repo.close()


def test_missing_session_is_reported_consistently(tmp_path):
    repo = SQLiteRepository(tmp_path / "agent.db")
    try:
        with pytest.raises(KeyError, match="session_not_found"):
            repo.get_session("missing")
        with pytest.raises(KeyError, match="session_not_found"):
            repo.add_message("missing", "user", "hello")
    finally:
        repo.close()
