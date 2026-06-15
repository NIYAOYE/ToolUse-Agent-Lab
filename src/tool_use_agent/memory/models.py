from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SessionRecord:
    id: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class MessageRecord:
    id: int
    session_id: str
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class ToolAuditRecord:
    id: int
    session_id: str
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class SummaryRecord:
    session_id: str
    content: dict[str, Any]
    covered_through_message_id: int
    updated_at: datetime
