from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any
from uuid import uuid4

from tool_use_agent.memory.models import (
    MessageRecord,
    SessionRecord,
    SummaryRecord,
    ToolAuditRecord,
)


class SQLiteRepository:
    def __init__(self, database_path: Path):
        self._database_path = Path(database_path).resolve()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            self._database_path,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def create_session(self, session_id: str | None = None) -> SessionRecord:
        identifier = session_id or str(uuid4())
        now = self._utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO sessions (id, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (identifier, now, now),
            )
        return self.get_session(identifier)

    def get_session(self, session_id: str) -> SessionRecord:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, created_at, updated_at
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            raise KeyError("session_not_found")
        return self._session_from_row(row)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> MessageRecord:
        now = self._utc_now()
        with self._lock, self._connection:
            self._require_session(session_id)
            cursor = self._connection.execute(
                """
                INSERT INTO messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, now),
            )
            self._touch_session(session_id, now)
            message_id = int(cursor.lastrowid)
        return MessageRecord(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            created_at=self._parse_datetime(now),
        )

    def list_messages(self, session_id: str) -> list[MessageRecord]:
        with self._lock:
            self._require_session(session_id)
            rows = self._connection.execute(
                """
                SELECT id, session_id, role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [self._message_from_row(row) for row in rows]

    def add_tool_audit(
        self,
        session_id: str,
        call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> ToolAuditRecord:
        now = self._utc_now()
        arguments_json = self._dump_json(arguments)
        result_json = self._dump_json(result)
        with self._lock, self._connection:
            self._require_session(session_id)
            cursor = self._connection.execute(
                """
                INSERT INTO tool_audits (
                    session_id,
                    call_id,
                    tool_name,
                    arguments_json,
                    result_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    call_id,
                    tool_name,
                    arguments_json,
                    result_json,
                    now,
                ),
            )
            self._touch_session(session_id, now)
            audit_id = int(cursor.lastrowid)
        return ToolAuditRecord(
            id=audit_id,
            session_id=session_id,
            call_id=call_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            created_at=self._parse_datetime(now),
        )

    def list_tool_audits(self, session_id: str) -> list[ToolAuditRecord]:
        with self._lock:
            self._require_session(session_id)
            rows = self._connection.execute(
                """
                SELECT
                    id,
                    session_id,
                    call_id,
                    tool_name,
                    arguments_json,
                    result_json,
                    created_at
                FROM tool_audits
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [self._tool_audit_from_row(row) for row in rows]

    def save_summary(
        self,
        session_id: str,
        content: dict[str, Any],
        *,
        covered_through_message_id: int,
    ) -> SummaryRecord:
        now = self._utc_now()
        content_json = self._dump_json(content)
        with self._lock, self._connection:
            self._require_session(session_id)
            self._connection.execute(
                """
                INSERT INTO summaries (
                    session_id,
                    content_json,
                    covered_through_message_id,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    content_json = excluded.content_json,
                    covered_through_message_id =
                        excluded.covered_through_message_id,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    content_json,
                    covered_through_message_id,
                    now,
                ),
            )
            self._touch_session(session_id, now)
        summary = self.get_summary(session_id)
        if summary is None:
            raise RuntimeError("summary_not_saved")
        return summary

    def get_summary(self, session_id: str) -> SummaryRecord | None:
        with self._lock:
            self._require_session(session_id)
            row = self._connection.execute(
                """
                SELECT
                    session_id,
                    content_json,
                    covered_through_message_id,
                    updated_at
                FROM summaries
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return self._summary_from_row(row)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _migrate(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                    ON messages(session_id, id);

                CREATE TABLE IF NOT EXISTS tool_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    call_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tool_audits_session_id
                    ON tool_audits(session_id, id);

                CREATE TABLE IF NOT EXISTS summaries (
                    session_id TEXT PRIMARY KEY,
                    content_json TEXT NOT NULL,
                    covered_through_message_id INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (covered_through_message_id)
                        REFERENCES messages(id)
                );
                """
            )

    def _require_session(self, session_id: str) -> None:
        row = self._connection.execute(
            "SELECT 1 FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise KeyError("session_not_found")

    def _touch_session(self, session_id: str, timestamp: str) -> None:
        self._connection.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (timestamp, session_id),
        )

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            id=row["id"],
            created_at=SQLiteRepository._parse_datetime(row["created_at"]),
            updated_at=SQLiteRepository._parse_datetime(row["updated_at"]),
        )

    @staticmethod
    def _message_from_row(row: sqlite3.Row) -> MessageRecord:
        return MessageRecord(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            created_at=SQLiteRepository._parse_datetime(row["created_at"]),
        )

    @staticmethod
    def _tool_audit_from_row(row: sqlite3.Row) -> ToolAuditRecord:
        return ToolAuditRecord(
            id=row["id"],
            session_id=row["session_id"],
            call_id=row["call_id"],
            tool_name=row["tool_name"],
            arguments=json.loads(row["arguments_json"]),
            result=json.loads(row["result_json"]),
            created_at=SQLiteRepository._parse_datetime(row["created_at"]),
        )

    @staticmethod
    def _summary_from_row(row: sqlite3.Row) -> SummaryRecord:
        return SummaryRecord(
            session_id=row["session_id"],
            content=json.loads(row["content_json"]),
            covered_through_message_id=row["covered_through_message_id"],
            updated_at=SQLiteRepository._parse_datetime(row["updated_at"]),
        )

    @staticmethod
    def _dump_json(value: dict[str, Any]) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)
