from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import RLock

from tool_use_agent.investigations.models import (
    Approval,
    ApprovalDecision,
    DiagnosisReport,
    DiagnosisTimeMetrics,
    Evidence,
    EvidenceKind,
    Investigation,
    InvestigationEvent,
    InvestigationStatus,
)
from tool_use_agent.tickets.models import (
    Attachment,
    Ticket,
    TicketPriority,
    TicketSource,
    TicketStatus,
    TicketDraft,
)
from tool_use_agent.tickets.state_machine import transition_ticket_status


class TicketAlreadyExists(ValueError):
    code = "ticket_already_exists"

    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id
        super().__init__(f"Ticket {ticket_id} already exists.")


class ActiveInvestigationExists(ValueError):
    code = "active_investigation_exists"

    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id
        super().__init__(f"Ticket {ticket_id} already has an active investigation.")


class InvalidEvidenceReference(ValueError):
    code = "invalid_evidence_reference"


class InvalidDiagnosisReport(ValueError):
    code = "invalid_diagnosis_report"


class SQLiteTicketRepository:
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

    def create_ticket(
        self,
        *,
        ticket_id: str,
        title: str,
        description: str,
        environment: str,
        service: str,
        priority: TicketPriority,
        category: str | None = None,
        source: TicketSource = TicketSource.MANUAL,
    ) -> Ticket:
        now = self._utc_now()
        try:
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    INSERT INTO tickets (
                        id,
                        title,
                        description,
                        environment,
                        service,
                        priority,
                        category,
                        status,
                        source,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticket_id,
                        title,
                        description,
                        environment,
                        service,
                        priority.value,
                        category,
                        TicketStatus.NEW.value,
                        source.value,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise TicketAlreadyExists(ticket_id) from exc
        return self.get_ticket(ticket_id)

    def create_tickets(
        self,
        drafts: list[TicketDraft],
        *,
        source: TicketSource,
    ) -> list[Ticket]:
        now = self._utc_now()
        try:
            with self._lock, self._connection:
                self._connection.executemany(
                    """
                    INSERT INTO tickets (
                        id,
                        title,
                        description,
                        environment,
                        service,
                        priority,
                        category,
                        status,
                        source,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            draft.id,
                            draft.title,
                            draft.description,
                            draft.environment,
                            draft.service,
                            draft.priority.value,
                            draft.category,
                            TicketStatus.NEW.value,
                            source.value,
                            now,
                            now,
                        )
                        for draft in drafts
                    ],
                )
        except sqlite3.IntegrityError as exc:
            raise TicketAlreadyExists("import_batch") from exc
        return [self.get_ticket(draft.id) for draft in drafts]

    def find_existing_ticket_ids(self, ticket_ids: list[str]) -> set[str]:
        if not ticket_ids:
            return set()
        placeholders = ",".join("?" for _ in ticket_ids)
        with self._lock:
            rows = self._connection.execute(
                f"SELECT id FROM tickets WHERE id IN ({placeholders})",
                ticket_ids,
            ).fetchall()
        return {row["id"] for row in rows}

    def get_ticket(self, ticket_id: str) -> Ticket:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    id,
                    title,
                    description,
                    environment,
                    service,
                    priority,
                    category,
                    status,
                    source,
                    created_at,
                    updated_at
                FROM tickets
                WHERE id = ?
                """,
                (ticket_id,),
            ).fetchone()
        if row is None:
            raise KeyError("ticket_not_found")
        return self._ticket_from_row(row)

    def delete_ticket(self, ticket_id: str) -> None:
        with self._lock, self._connection:
            self._require_ticket(ticket_id)
            self._connection.execute(
                "DELETE FROM tickets WHERE id = ?",
                (ticket_id,),
            )

    def list_tickets(
        self,
        *,
        offset: int,
        limit: int,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Ticket], int]:
        sort_columns = {
            "created_at": "created_at",
            "updated_at": "updated_at",
            "priority": "priority",
        }
        if sort_by not in sort_columns:
            raise ValueError("invalid_ticket_sort_field")
        normalized_order = sort_order.lower()
        if normalized_order not in {"asc", "desc"}:
            raise ValueError("invalid_ticket_sort_order")

        conditions: list[str] = []
        parameters: list[object] = []
        if status is not None:
            conditions.append("status = ?")
            parameters.append(status.value)
        if priority is not None:
            conditions.append("priority = ?")
            parameters.append(priority.value)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        column = sort_columns[sort_by]

        with self._lock:
            total = int(
                self._connection.execute(
                    f"SELECT COUNT(*) FROM tickets {where_clause}",
                    parameters,
                ).fetchone()[0]
            )
            rows = self._connection.execute(
                f"""
                SELECT
                    id,
                    title,
                    description,
                    environment,
                    service,
                    priority,
                    category,
                    status,
                    source,
                    created_at,
                    updated_at
                FROM tickets
                {where_clause}
                ORDER BY {column} {normalized_order.upper()}, id ASC
                LIMIT ? OFFSET ?
                """,
                (*parameters, limit, offset),
            ).fetchall()
        return [self._ticket_from_row(row) for row in rows], total

    def add_attachment(
        self,
        ticket_id: str,
        *,
        original_filename: str,
        stored_path: str,
        media_type: str,
        size_bytes: int,
    ) -> Attachment:
        now = self._utc_now()
        with self._lock, self._connection:
            self._require_ticket(ticket_id)
            cursor = self._connection.execute(
                """
                INSERT INTO attachments (
                    ticket_id,
                    original_filename,
                    stored_path,
                    media_type,
                    size_bytes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    original_filename,
                    stored_path,
                    media_type,
                    size_bytes,
                    now,
                ),
            )
            attachment_id = int(cursor.lastrowid)
        return Attachment(
            id=attachment_id,
            ticket_id=ticket_id,
            original_filename=original_filename,
            stored_path=stored_path,
            media_type=media_type,
            size_bytes=size_bytes,
            created_at=self._parse_datetime(now),
        )

    def list_attachments(self, ticket_id: str) -> list[Attachment]:
        with self._lock:
            self._require_ticket(ticket_id)
            rows = self._connection.execute(
                """
                SELECT
                    id,
                    ticket_id,
                    original_filename,
                    stored_path,
                    media_type,
                    size_bytes,
                    created_at
                FROM attachments
                WHERE ticket_id = ?
                ORDER BY id ASC
                """,
                (ticket_id,),
            ).fetchall()
        return [self._attachment_from_row(row) for row in rows]

    def get_attachment_total_bytes(self, ticket_id: str) -> int:
        with self._lock:
            self._require_ticket(ticket_id)
            row = self._connection.execute(
                """
                SELECT COALESCE(SUM(size_bytes), 0) AS total_bytes
                FROM attachments
                WHERE ticket_id = ?
                """,
                (ticket_id,),
            ).fetchone()
        return int(row["total_bytes"])

    def create_investigation(
        self,
        ticket_id: str,
        session_id: str,
    ) -> Investigation:
        now = self._utc_now()
        with self._lock, self._connection:
            self._require_ticket(ticket_id)
            self._require_session(session_id)
            active = self._connection.execute(
                """
                SELECT 1
                FROM investigations
                WHERE ticket_id = ? AND completed_at IS NULL
                """,
                (ticket_id,),
            ).fetchone()
            if active is not None:
                raise ActiveInvestigationExists(ticket_id)
            try:
                cursor = self._connection.execute(
                    """
                    INSERT INTO investigations (
                        ticket_id,
                        session_id,
                        status,
                        started_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        ticket_id,
                        session_id,
                        InvestigationStatus.INVESTIGATING.value,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ActiveInvestigationExists(ticket_id) from exc
            investigation_id = int(cursor.lastrowid)
        return self.get_investigation(investigation_id)

    def get_investigation(self, investigation_id: int) -> Investigation:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    id,
                    ticket_id,
                    session_id,
                    status,
                    started_at,
                    diagnosed_at,
                    completed_at,
                    stop_reason,
                    supplemental_instructions
                FROM investigations
                WHERE id = ?
                """,
                (investigation_id,),
            ).fetchone()
        if row is None:
            raise KeyError("investigation_not_found")
        return self._investigation_from_row(row)

    def get_current_investigation(
        self,
        ticket_id: str,
    ) -> Investigation | None:
        with self._lock:
            self._require_ticket(ticket_id)
            row = self._connection.execute(
                """
                SELECT
                    id,
                    ticket_id,
                    session_id,
                    status,
                    started_at,
                    diagnosed_at,
                    completed_at,
                    stop_reason,
                    supplemental_instructions
                FROM investigations
                WHERE ticket_id = ? AND completed_at IS NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (ticket_id,),
            ).fetchone()
        return self._investigation_from_row(row) if row is not None else None

    def mark_investigation_awaiting_review(
        self,
        investigation_id: int,
    ) -> Investigation:
        now = self._utc_now()
        with self._lock, self._connection:
            self.get_investigation(investigation_id)
            self._connection.execute(
                """
                UPDATE investigations
                SET status = ?,
                    diagnosed_at = COALESCE(diagnosed_at, ?),
                    stop_reason = NULL
                WHERE id = ?
                """,
                (
                    InvestigationStatus.AWAITING_REVIEW.value,
                    now,
                    investigation_id,
                ),
            )
        return self.get_investigation(investigation_id)

    def mark_investigation_investigating(
        self,
        investigation_id: int,
        *,
        supplemental_instructions: str | None = None,
    ) -> Investigation:
        with self._lock, self._connection:
            self.get_investigation(investigation_id)
            self._connection.execute(
                """
                UPDATE investigations
                SET status = ?,
                    stop_reason = NULL,
                    supplemental_instructions = ?
                WHERE id = ?
                """,
                (
                    InvestigationStatus.INVESTIGATING.value,
                    supplemental_instructions,
                    investigation_id,
                ),
            )
        return self.get_investigation(investigation_id)

    def mark_investigation_approved(
        self,
        investigation_id: int,
    ) -> Investigation:
        now = self._utc_now()
        with self._lock, self._connection:
            self.get_investigation(investigation_id)
            self._connection.execute(
                """
                UPDATE investigations
                SET status = ?, completed_at = ?, stop_reason = NULL
                WHERE id = ?
                """,
                (
                    InvestigationStatus.APPROVED.value,
                    now,
                    investigation_id,
                ),
            )
        return self.get_investigation(investigation_id)

    def mark_investigation_failed(
        self,
        investigation_id: int,
        *,
        stop_reason: str,
    ) -> Investigation:
        with self._lock, self._connection:
            self.get_investigation(investigation_id)
            self._connection.execute(
                """
                UPDATE investigations
                SET status = ?, stop_reason = ?
                WHERE id = ?
                """,
                (
                    InvestigationStatus.FAILED.value,
                    stop_reason,
                    investigation_id,
                ),
            )
        return self.get_investigation(investigation_id)

    def add_evidence(
        self,
        investigation_id: int,
        *,
        kind: EvidenceKind,
        title: str,
        summary: str,
        source_ref: str | None = None,
        tool_audit_id: int | None = None,
        attachment_id: int | None = None,
    ) -> Evidence:
        now = self._utc_now()
        with self._lock, self._connection:
            investigation = self.get_investigation(investigation_id)
            self._validate_evidence_reference(
                investigation,
                kind=kind,
                source_ref=source_ref,
                tool_audit_id=tool_audit_id,
                attachment_id=attachment_id,
            )
            cursor = self._connection.execute(
                """
                INSERT INTO evidence (
                    investigation_id,
                    kind,
                    title,
                    summary,
                    source_ref,
                    tool_audit_id,
                    attachment_id,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    investigation_id,
                    kind.value,
                    title,
                    summary,
                    source_ref,
                    tool_audit_id,
                    attachment_id,
                    now,
                ),
            )
            evidence_id = int(cursor.lastrowid)
        return Evidence(
            id=evidence_id,
            investigation_id=investigation_id,
            kind=kind,
            title=title,
            summary=summary,
            source_ref=source_ref,
            tool_audit_id=tool_audit_id,
            attachment_id=attachment_id,
            created_at=self._parse_datetime(now),
        )

    def list_evidence(self, investigation_id: int) -> list[Evidence]:
        with self._lock:
            self.get_investigation(investigation_id)
            rows = self._connection.execute(
                """
                SELECT
                    id,
                    investigation_id,
                    kind,
                    title,
                    summary,
                    source_ref,
                    tool_audit_id,
                    attachment_id,
                    created_at
                FROM evidence
                WHERE investigation_id = ?
                ORDER BY id ASC
                """,
                (investigation_id,),
            ).fetchall()
        return [self._evidence_from_row(row) for row in rows]

    def add_investigation_event(
        self,
        investigation_id: int,
        event: str,
        payload: dict[str, object],
    ) -> InvestigationEvent:
        now = self._utc_now()
        with self._lock, self._connection:
            self.get_investigation(investigation_id)
            cursor = self._connection.execute(
                """
                INSERT INTO investigation_events (
                    investigation_id,
                    event,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    investigation_id,
                    event,
                    json.dumps(payload, ensure_ascii=False),
                    now,
                ),
            )
            event_id = int(cursor.lastrowid)
        return InvestigationEvent(
            id=event_id,
            investigation_id=investigation_id,
            event=event,
            payload=dict(payload),
            created_at=self._parse_datetime(now),
        )

    def list_investigation_events(
        self,
        investigation_id: int,
        *,
        after_id: int = 0,
    ) -> list[InvestigationEvent]:
        with self._lock:
            self.get_investigation(investigation_id)
            rows = self._connection.execute(
                """
                SELECT id, investigation_id, event, payload_json, created_at
                FROM investigation_events
                WHERE investigation_id = ? AND id > ?
                ORDER BY id ASC
                """,
                (investigation_id, after_id),
            ).fetchall()
        return [
            InvestigationEvent(
                id=row["id"],
                investigation_id=row["investigation_id"],
                event=row["event"],
                payload=json.loads(row["payload_json"]),
                created_at=self._parse_datetime(row["created_at"]),
            )
            for row in rows
        ]

    def get_diagnosis_time_metrics(self) -> DiagnosisTimeMetrics:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT started_at, diagnosed_at
                FROM investigations
                WHERE diagnosed_at IS NOT NULL
                ORDER BY diagnosed_at ASC
                """
            ).fetchall()
        values = sorted(
            (
                self._parse_datetime(row["diagnosed_at"])
                - self._parse_datetime(row["started_at"])
            ).total_seconds()
            for row in rows
        )
        if not values:
            return DiagnosisTimeMetrics(0, None, None)
        middle = len(values) // 2
        if len(values) % 2:
            median = values[middle]
        else:
            median = (values[middle - 1] + values[middle]) / 2
        position = (len(values) - 1) * 0.75
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        fraction = position - lower
        p75 = values[lower] + (values[upper] - values[lower]) * fraction
        return DiagnosisTimeMetrics(len(values), median, p75)

    def save_diagnosis_report(
        self,
        investigation_id: int,
        *,
        category: str,
        suggested_priority: TicketPriority,
        root_cause: str,
        confidence: float,
        evidence_ids: list[int],
        recommended_actions: list[str],
        reply_draft: str,
    ) -> DiagnosisReport:
        evidence_ids_tuple = tuple(evidence_ids)
        if not 0 <= confidence <= 1:
            raise InvalidDiagnosisReport("confidence must be between 0 and 1")
        if len(set(evidence_ids_tuple)) != len(evidence_ids_tuple):
            raise InvalidDiagnosisReport("evidence ids must be unique")

        now = self._utc_now()
        with self._lock, self._connection:
            self.get_investigation(investigation_id)
            if evidence_ids_tuple:
                placeholders = ",".join("?" for _ in evidence_ids_tuple)
                rows = self._connection.execute(
                    f"""
                    SELECT id
                    FROM evidence
                    WHERE investigation_id = ?
                        AND id IN ({placeholders})
                    """,
                    (investigation_id, *evidence_ids_tuple),
                ).fetchall()
                if {row["id"] for row in rows} != set(evidence_ids_tuple):
                    raise InvalidDiagnosisReport(
                        "all evidence must belong to the investigation"
                    )
            cursor = self._connection.execute(
                """
                INSERT INTO diagnosis_reports (
                    investigation_id,
                    category,
                    suggested_priority,
                    root_cause,
                    confidence,
                    recommended_actions_json,
                    reply_draft,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    investigation_id,
                    category,
                    suggested_priority.value,
                    root_cause,
                    confidence,
                    json.dumps(recommended_actions, ensure_ascii=False),
                    reply_draft,
                    now,
                ),
            )
            report_id = int(cursor.lastrowid)
            self._connection.executemany(
                """
                INSERT INTO diagnosis_report_evidence (
                    report_id,
                    evidence_id,
                    position
                )
                VALUES (?, ?, ?)
                """,
                [
                    (report_id, evidence_id, position)
                    for position, evidence_id in enumerate(evidence_ids_tuple)
                ],
            )
        report = self.get_diagnosis_report(investigation_id)
        if report is None:
            raise RuntimeError("diagnosis_report_not_saved")
        return report

    def get_diagnosis_report(
        self,
        investigation_id: int,
    ) -> DiagnosisReport | None:
        with self._lock:
            self.get_investigation(investigation_id)
            row = self._connection.execute(
                """
                SELECT
                    id,
                    investigation_id,
                    category,
                    suggested_priority,
                    root_cause,
                    confidence,
                    recommended_actions_json,
                    reply_draft,
                    created_at
                FROM diagnosis_reports
                WHERE investigation_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (investigation_id,),
            ).fetchone()
            if row is None:
                return None
            evidence_rows = self._connection.execute(
                """
                SELECT evidence_id
                FROM diagnosis_report_evidence
                WHERE report_id = ?
                ORDER BY position ASC
                """,
                (row["id"],),
            ).fetchall()
        return self._diagnosis_report_from_row(
            row,
            tuple(item["evidence_id"] for item in evidence_rows),
        )

    def add_approval(
        self,
        investigation_id: int,
        *,
        decision: ApprovalDecision,
        original_draft: str,
        final_draft: str,
        review_notes: str,
    ) -> Approval:
        now = self._utc_now()
        with self._lock, self._connection:
            self.get_investigation(investigation_id)
            cursor = self._connection.execute(
                """
                INSERT INTO approvals (
                    investigation_id,
                    decision,
                    original_draft,
                    final_draft,
                    review_notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    investigation_id,
                    decision.value,
                    original_draft,
                    final_draft,
                    review_notes,
                    now,
                ),
            )
            approval_id = int(cursor.lastrowid)
        return Approval(
            id=approval_id,
            investigation_id=investigation_id,
            decision=decision,
            original_draft=original_draft,
            final_draft=final_draft,
            review_notes=review_notes,
            created_at=self._parse_datetime(now),
        )

    def list_approvals(self, investigation_id: int) -> list[Approval]:
        with self._lock:
            self.get_investigation(investigation_id)
            rows = self._connection.execute(
                """
                SELECT
                    id,
                    investigation_id,
                    decision,
                    original_draft,
                    final_draft,
                    review_notes,
                    created_at
                FROM approvals
                WHERE investigation_id = ?
                ORDER BY id ASC
                """,
                (investigation_id,),
            ).fetchall()
        return [self._approval_from_row(row) for row in rows]

    def transition_status(
        self,
        ticket_id: str,
        target: TicketStatus,
    ) -> Ticket:
        with self._lock, self._connection:
            current = self.get_ticket(ticket_id)
            status = transition_ticket_status(current.status, target)
            self._connection.execute(
                """
                UPDATE tickets
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.value, self._utc_now(), ticket_id),
            )
        return self.get_ticket(ticket_id)

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

                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    service TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    category TEXT,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tickets_status_priority
                    ON tickets(status, priority, created_at);

                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_attachments_ticket_id
                    ON attachments(ticket_id, id);

                CREATE TABLE IF NOT EXISTS investigations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    diagnosed_at TEXT,
                    completed_at TEXT,
                    stop_reason TEXT,
                    supplemental_instructions TEXT,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_investigations_one_active_per_ticket
                    ON investigations(ticket_id)
                    WHERE completed_at IS NULL;

                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_ref TEXT,
                    tool_audit_id INTEGER,
                    attachment_id INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (investigation_id) REFERENCES investigations(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (tool_audit_id) REFERENCES tool_audits(id),
                    FOREIGN KEY (attachment_id) REFERENCES attachments(id)
                );

                CREATE INDEX IF NOT EXISTS idx_evidence_investigation_id
                    ON evidence(investigation_id, id);

                CREATE TABLE IF NOT EXISTS investigation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id INTEGER NOT NULL,
                    event TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (investigation_id) REFERENCES investigations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_investigation_events_resume
                    ON investigation_events(investigation_id, id);

                CREATE TABLE IF NOT EXISTS diagnosis_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    suggested_priority TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    recommended_actions_json TEXT NOT NULL,
                    reply_draft TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (investigation_id) REFERENCES investigations(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS diagnosis_report_evidence (
                    report_id INTEGER NOT NULL,
                    evidence_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (report_id, evidence_id),
                    UNIQUE (report_id, position),
                    FOREIGN KEY (report_id) REFERENCES diagnosis_reports(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (evidence_id) REFERENCES evidence(id)
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id INTEGER NOT NULL,
                    decision TEXT NOT NULL,
                    original_draft TEXT NOT NULL,
                    final_draft TEXT NOT NULL,
                    review_notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (investigation_id) REFERENCES investigations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_approvals_investigation_id
                    ON approvals(investigation_id, id);
                """
            )

    def _validate_evidence_reference(
        self,
        investigation: Investigation,
        *,
        kind: EvidenceKind,
        source_ref: str | None,
        tool_audit_id: int | None,
        attachment_id: int | None,
    ) -> None:
        if kind is EvidenceKind.TOOL_RESULT:
            if tool_audit_id is None:
                raise InvalidEvidenceReference("tool audit is required")
            row = self._connection.execute(
                "SELECT session_id FROM tool_audits WHERE id = ?",
                (tool_audit_id,),
            ).fetchone()
            if row is None or row["session_id"] != investigation.session_id:
                raise InvalidEvidenceReference(
                    "tool audit must belong to the investigation session"
                )
        elif kind is EvidenceKind.WEB_SOURCE:
            if source_ref is None or not source_ref.startswith(("http://", "https://")):
                raise InvalidEvidenceReference("web source URL is required")
        elif kind is EvidenceKind.ATTACHMENT:
            if attachment_id is None or not source_ref:
                raise InvalidEvidenceReference(
                    "attachment and fragment reference are required"
                )
            row = self._connection.execute(
                "SELECT ticket_id FROM attachments WHERE id = ?",
                (attachment_id,),
            ).fetchone()
            if row is None or row["ticket_id"] != investigation.ticket_id:
                raise InvalidEvidenceReference(
                    "attachment must belong to the investigation ticket"
                )

    def _require_ticket(self, ticket_id: str) -> None:
        row = self._connection.execute(
            "SELECT 1 FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        if row is None:
            raise KeyError("ticket_not_found")

    def _require_session(self, session_id: str) -> None:
        try:
            row = self._connection.execute(
                "SELECT 1 FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            raise KeyError("session_not_found") from exc
        if row is None:
            raise KeyError("session_not_found")

    @staticmethod
    def _ticket_from_row(row: sqlite3.Row) -> Ticket:
        return Ticket(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            environment=row["environment"],
            service=row["service"],
            priority=TicketPriority(row["priority"]),
            category=row["category"],
            status=TicketStatus(row["status"]),
            source=TicketSource(row["source"]),
            created_at=SQLiteTicketRepository._parse_datetime(row["created_at"]),
            updated_at=SQLiteTicketRepository._parse_datetime(row["updated_at"]),
        )

    @staticmethod
    def _attachment_from_row(row: sqlite3.Row) -> Attachment:
        return Attachment(
            id=row["id"],
            ticket_id=row["ticket_id"],
            original_filename=row["original_filename"],
            stored_path=row["stored_path"],
            media_type=row["media_type"],
            size_bytes=row["size_bytes"],
            created_at=SQLiteTicketRepository._parse_datetime(row["created_at"]),
        )

    @staticmethod
    def _investigation_from_row(row: sqlite3.Row) -> Investigation:
        parse = SQLiteTicketRepository._parse_datetime
        return Investigation(
            id=row["id"],
            ticket_id=row["ticket_id"],
            session_id=row["session_id"],
            status=InvestigationStatus(row["status"]),
            started_at=parse(row["started_at"]),
            diagnosed_at=parse(row["diagnosed_at"])
            if row["diagnosed_at"]
            else None,
            completed_at=parse(row["completed_at"])
            if row["completed_at"]
            else None,
            stop_reason=row["stop_reason"],
            supplemental_instructions=row["supplemental_instructions"],
        )

    @staticmethod
    def _evidence_from_row(row: sqlite3.Row) -> Evidence:
        return Evidence(
            id=row["id"],
            investigation_id=row["investigation_id"],
            kind=EvidenceKind(row["kind"]),
            title=row["title"],
            summary=row["summary"],
            source_ref=row["source_ref"],
            tool_audit_id=row["tool_audit_id"],
            attachment_id=row["attachment_id"],
            created_at=SQLiteTicketRepository._parse_datetime(row["created_at"]),
        )

    @staticmethod
    def _diagnosis_report_from_row(
        row: sqlite3.Row,
        evidence_ids: tuple[int, ...],
    ) -> DiagnosisReport:
        return DiagnosisReport(
            id=row["id"],
            investigation_id=row["investigation_id"],
            category=row["category"],
            suggested_priority=TicketPriority(row["suggested_priority"]),
            root_cause=row["root_cause"],
            confidence=row["confidence"],
            evidence_ids=evidence_ids,
            recommended_actions=tuple(
                json.loads(row["recommended_actions_json"])
            ),
            reply_draft=row["reply_draft"],
            created_at=SQLiteTicketRepository._parse_datetime(row["created_at"]),
        )

    @staticmethod
    def _approval_from_row(row: sqlite3.Row) -> Approval:
        return Approval(
            id=row["id"],
            investigation_id=row["investigation_id"],
            decision=ApprovalDecision(row["decision"]),
            original_draft=row["original_draft"],
            final_draft=row["final_draft"],
            review_notes=row["review_notes"],
            created_at=SQLiteTicketRepository._parse_datetime(row["created_at"]),
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)
