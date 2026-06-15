from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TicketPriority(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TicketSource(StrEnum):
    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    JSON_IMPORT = "json_import"


class TicketStatus(StrEnum):
    NEW = "NEW"
    QUEUED = "QUEUED"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    FAILED = "FAILED"
    APPROVED = "APPROVED"


@dataclass(frozen=True)
class Ticket:
    id: str
    title: str
    description: str
    environment: str
    service: str
    priority: TicketPriority
    category: str | None
    status: TicketStatus
    source: TicketSource
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Attachment:
    id: int
    ticket_id: str
    original_filename: str
    stored_path: str
    media_type: str
    size_bytes: int
    created_at: datetime
