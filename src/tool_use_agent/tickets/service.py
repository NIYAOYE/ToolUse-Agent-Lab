from dataclasses import dataclass
from collections import Counter
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from uuid import uuid4

from tool_use_agent.investigations.models import DiagnosisReport, Investigation
from tool_use_agent.tickets.models import (
    Ticket,
    Attachment,
    TicketDraft,
    TicketPriority,
    TicketSource,
    TicketStatus,
)
from tool_use_agent.tickets.repository import (
    SQLiteTicketRepository,
    TicketAlreadyExists,
)


@dataclass(frozen=True)
class TicketPage:
    items: tuple[Ticket, ...]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class TicketDetail:
    ticket: Ticket
    current_investigation: Investigation | None
    diagnosis_report: DiagnosisReport | None


class TicketImportValidationError(ValueError):
    code = "ticket_import_validation_failed"

    def __init__(self, errors: list[dict[str, object]]):
        self.errors = errors
        super().__init__("Ticket import validation failed.")


class TicketImportTooLarge(ValueError):
    code = "ticket_import_too_large"


class AttachmentValidationError(ValueError):
    code = "invalid_attachment"


class AttachmentTooLarge(ValueError):
    code = "attachment_too_large"


class TicketService:
    _ALLOWED_ATTACHMENT_MEDIA_TYPES = {
        ".log": {"text/plain"},
        ".txt": {"text/plain"},
        ".csv": {"text/csv", "application/vnd.ms-excel"},
        ".json": {"application/json"},
    }

    def __init__(
        self,
        repository: SQLiteTicketRepository,
        *,
        workspace_root: Path | None = None,
        max_import_bytes: int = 1_000_000,
        max_attachment_bytes: int = 1_000_000,
        max_ticket_attachment_bytes: int = 5_000_000,
    ):
        self._repository = repository
        self._workspace_root = (workspace_root or Path("workspace")).resolve()
        self._max_import_bytes = max(1, int(max_import_bytes))
        self._max_attachment_bytes = max(1, int(max_attachment_bytes))
        self._max_ticket_attachment_bytes = max(
            self._max_attachment_bytes,
            int(max_ticket_attachment_bytes),
        )

    @property
    def max_import_bytes(self) -> int:
        return self._max_import_bytes

    @property
    def max_attachment_bytes(self) -> int:
        return self._max_attachment_bytes

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
        return self._repository.create_ticket(
            ticket_id=ticket_id,
            title=title,
            description=description,
            environment=environment,
            service=service,
            priority=priority,
            category=category,
            source=source,
        )

    def list_tickets(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> TicketPage:
        items, total = self._repository.list_tickets(
            offset=(page - 1) * page_size,
            limit=page_size,
            status=status,
            priority=priority,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return TicketPage(
            items=tuple(items),
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_ticket_detail(self, ticket_id: str) -> TicketDetail:
        ticket = self._repository.get_ticket(ticket_id)
        investigation = self._repository.get_current_investigation(ticket_id)
        report = (
            self._repository.get_diagnosis_report(investigation.id)
            if investigation is not None
            else None
        )
        return TicketDetail(
            ticket=ticket,
            current_investigation=investigation,
            diagnosis_report=report,
        )

    def delete_ticket(self, ticket_id: str) -> None:
        attachments = self._repository.list_attachments(ticket_id)
        self._repository.delete_ticket(ticket_id)
        for attachment in attachments:
            target = (self._workspace_root / attachment.stored_path).resolve()
            if not target.is_relative_to(self._workspace_root):
                continue
            target.unlink(missing_ok=True)
            self._remove_empty_attachment_dirs(target.parent)

    def import_tickets(self, filename: str, content: bytes) -> list[Ticket]:
        if len(content) > self._max_import_bytes:
            raise TicketImportTooLarge("Ticket import exceeds the file size limit.")
        suffix = Path(filename).suffix.lower()
        if suffix == ".json":
            rows = self._parse_json_import(content)
            source = TicketSource.JSON_IMPORT
        elif suffix == ".csv":
            rows = self._parse_csv_import(content)
            source = TicketSource.CSV_IMPORT
        else:
            raise TicketImportValidationError(
                [{"row": 0, "field": "file", "message": "Use CSV or JSON."}]
            )
        if not rows:
            raise TicketImportValidationError(
                [{"row": 0, "field": "file", "message": "Import is empty."}]
            )

        validated, errors = self._validate_import_rows(rows)
        drafts = [draft for _, draft in validated]
        row_by_id = {draft.id: row_number for row_number, draft in validated}
        id_counts = Counter(draft.id for draft in drafts)
        duplicate_ids = {
            ticket_id for ticket_id, count in id_counts.items() if count > 1
        }
        duplicate_ids.update(
            self._repository.find_existing_ticket_ids([draft.id for draft in drafts])
        )
        errors.extend(
            {
                "row": row_by_id[ticket_id],
                "field": "id",
                "message": f"Duplicate ticket id: {ticket_id}",
            }
            for ticket_id in sorted(duplicate_ids)
        )
        if errors:
            raise TicketImportValidationError(errors)
        try:
            return self._repository.create_tickets(drafts, source=source)
        except TicketAlreadyExists as exc:
            raise TicketImportValidationError(
                [{"row": 0, "field": "id", "message": "Duplicate ticket id."}]
            ) from exc

    def save_attachment(
        self,
        ticket_id: str,
        *,
        filename: str,
        media_type: str,
        content: bytes,
    ) -> Attachment:
        self._repository.get_ticket(ticket_id)
        self._validate_attachment(filename, media_type, content)
        current_total = self._repository.get_attachment_total_bytes(ticket_id)
        if current_total + len(content) > self._max_ticket_attachment_bytes:
            raise AttachmentTooLarge("Ticket attachment total size limit exceeded.")

        ticket_key = sha256(ticket_id.encode("utf-8")).hexdigest()[:20]
        relative_path = (
            Path("tickets")
            / ticket_key
            / "attachments"
            / f"{uuid4().hex}_{filename}"
        )
        target = (self._workspace_root / relative_path).resolve()
        if not target.is_relative_to(self._workspace_root):
            raise AttachmentValidationError("Attachment path is outside workspace.")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)
        try:
            return self._repository.add_attachment(
                ticket_id,
                original_filename=filename,
                stored_path=relative_path.as_posix(),
                media_type=media_type,
                size_bytes=len(content),
            )
        except Exception:
            target.unlink(missing_ok=True)
            raise

    @staticmethod
    def _decode_import(content: bytes) -> str:
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                return content.decode("gb18030")
            except UnicodeDecodeError as exc:
                raise TicketImportValidationError(
                    [
                        {
                            "row": 0,
                            "field": "file",
                            "message": "File must be UTF-8 or GB18030 text.",
                        }
                    ]
                ) from exc

    def _parse_json_import(
        self,
        content: bytes,
    ) -> list[tuple[int, dict[str, object]]]:
        try:
            payload = json.loads(self._decode_import(content))
        except json.JSONDecodeError as exc:
            raise TicketImportValidationError(
                [{"row": exc.lineno, "field": "file", "message": "Invalid JSON."}]
            ) from exc
        if not isinstance(payload, list):
            raise TicketImportValidationError(
                [{"row": 0, "field": "file", "message": "JSON must be an array."}]
            )
        return [
            (index, item if isinstance(item, dict) else {})
            for index, item in enumerate(payload, start=1)
        ]

    def _parse_csv_import(
        self,
        content: bytes,
    ) -> list[tuple[int, dict[str, object]]]:
        reader = csv.DictReader(StringIO(self._decode_import(content)))
        if reader.fieldnames is None:
            raise TicketImportValidationError(
                [{"row": 1, "field": "file", "message": "CSV header is required."}]
            )
        required = {"id", "title", "description", "environment", "service", "priority"}
        missing = sorted(required - {name.strip() for name in reader.fieldnames})
        if missing:
            raise TicketImportValidationError(
                [
                    {
                        "row": 1,
                        "field": field,
                        "message": "CSV column is required.",
                    }
                    for field in missing
                ]
            )
        return [(index, dict(row)) for index, row in enumerate(reader, start=2)]

    @staticmethod
    def _validate_import_rows(
        rows: list[tuple[int, dict[str, object]]],
    ) -> tuple[list[tuple[int, TicketDraft]], list[dict[str, object]]]:
        required = ("id", "title", "description", "environment", "service", "priority")
        drafts: list[tuple[int, TicketDraft]] = []
        errors: list[dict[str, object]] = []
        for row_number, row in rows:
            row_errors = False
            values: dict[str, str] = {}
            for field in required:
                value = str(row.get(field, "") or "").strip()
                values[field] = value
                if not value:
                    errors.append(
                        {"row": row_number, "field": field, "message": "Field is required."}
                    )
                    row_errors = True
            try:
                priority = TicketPriority(values.get("priority", ""))
            except ValueError:
                errors.append(
                    {
                        "row": row_number,
                        "field": "priority",
                        "message": "Priority must be P1, P2, P3, or P4.",
                    }
                )
                row_errors = True
                priority = TicketPriority.P4
            if row_errors:
                continue
            drafts.append(
                (
                    row_number,
                    TicketDraft(
                        id=values["id"],
                        title=values["title"],
                        description=values["description"],
                        environment=values["environment"],
                        service=values["service"],
                        priority=priority,
                        category=str(row.get("category", "") or "").strip()
                        or None,
                    ),
                )
            )
        return drafts, errors

    def _validate_attachment(
        self,
        filename: str,
        media_type: str,
        content: bytes,
    ) -> None:
        if not filename or Path(filename).name != filename or any(
            separator in filename for separator in ("/", "\\")
        ):
            raise AttachmentValidationError("Attachment filename is invalid.")
        suffix = Path(filename).suffix.lower()
        allowed_media_types = self._ALLOWED_ATTACHMENT_MEDIA_TYPES.get(suffix)
        if allowed_media_types is None or media_type not in allowed_media_types:
            raise AttachmentValidationError("Attachment type is not allowed.")
        if len(content) > self._max_attachment_bytes:
            raise AttachmentTooLarge("Attachment exceeds the single-file size limit.")
        if b"\x00" in content:
            raise AttachmentValidationError("Binary attachments are not allowed.")
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                decoded = content.decode("gb18030")
            except UnicodeDecodeError as exc:
                raise AttachmentValidationError(
                    "Attachment must be UTF-8 or GB18030 text."
                ) from exc
        if suffix == ".json":
            try:
                json.loads(decoded)
            except json.JSONDecodeError as exc:
                raise AttachmentValidationError(
                    "JSON attachment content is invalid."
                ) from exc

    def _remove_empty_attachment_dirs(self, directory: Path) -> None:
        root = self._workspace_root.resolve()
        current = directory.resolve()
        while current != root and current.is_relative_to(root):
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def close(self) -> None:
        self._repository.close()
