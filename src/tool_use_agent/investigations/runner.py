from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from tool_use_agent.investigations.models import (
    DiagnosisReport,
    Evidence,
    EvidenceKind,
    Investigation,
)
from tool_use_agent.investigations.prompts import INVESTIGATION_SYSTEM_PROMPT
from tool_use_agent.memory.repository import SQLiteRepository
from tool_use_agent.tickets.models import TicketPriority, TicketStatus
from tool_use_agent.tickets.repository import SQLiteTicketRepository


class AgentRunner(Protocol):
    def invoke(self, state: dict[str, Any]) -> dict[str, Any]: ...


class EvidenceDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    kind: EvidenceKind
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_ref: str | None = None
    tool_call_id: str | None = None
    attachment_id: int | None = Field(default=None, gt=0)


class DiagnosisDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1)
    suggested_priority: TicketPriority
    root_cause: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence_keys: list[str]
    recommended_actions: list[str] = Field(min_length=1)
    reply_draft: str = Field(min_length=1)


class InvestigationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[EvidenceDraft]
    report: DiagnosisDraft

    @model_validator(mode="after")
    def validate_evidence_keys(self) -> InvestigationOutput:
        keys = [item.key for item in self.evidence]
        if len(set(keys)) != len(keys):
            raise ValueError("evidence keys must be unique")
        if len(set(self.report.evidence_keys)) != len(
            self.report.evidence_keys
        ):
            raise ValueError("report evidence keys must be unique")
        if not set(self.report.evidence_keys).issubset(keys):
            raise ValueError("report cites unknown evidence keys")
        return self


@dataclass(frozen=True)
class InvestigationRunResult:
    investigation: Investigation
    report: DiagnosisReport
    evidence: tuple[Evidence, ...]
    events: tuple[dict[str, Any], ...]


class InvestigationRunError(RuntimeError):
    code = "investigation_run_failed"

    def __init__(self, stop_reason: str):
        self.stop_reason = stop_reason
        super().__init__(stop_reason)


class _EvidenceValidationError(ValueError):
    pass


class InvestigationRunner:
    def __init__(
        self,
        *,
        ticket_repository: SQLiteTicketRepository,
        memory_repository: SQLiteRepository,
        agent_runner: AgentRunner,
    ) -> None:
        self._tickets = ticket_repository
        self._memory = memory_repository
        self._agent = agent_runner

    def run(self, investigation_id: int) -> InvestigationRunResult:
        investigation = self._tickets.get_investigation(investigation_id)
        ticket = self._tickets.get_ticket(investigation.ticket_id)
        attachments = self._tickets.list_attachments(ticket.id)
        context = {
            "ticket": {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "environment": ticket.environment,
                "service": ticket.service,
                "priority": ticket.priority.value,
                "category": ticket.category,
            },
            "attachments": [
                {
                    "id": attachment.id,
                    "filename": attachment.original_filename,
                    "media_type": attachment.media_type,
                    "path": attachment.stored_path,
                    "size_bytes": attachment.size_bytes,
                }
                for attachment in attachments
            ],
            "supplemental_instructions": (
                investigation.supplemental_instructions
            ),
        }
        context_json = json.dumps(context, ensure_ascii=False)
        messages = [
            SystemMessage(content=INVESTIGATION_SYSTEM_PROMPT),
            HumanMessage(content=context_json),
        ]
        self._memory.add_message(
            investigation.session_id,
            "user",
            context_json,
        )

        try:
            state = self._agent.invoke(
                {"messages": messages, "tool_steps": 0, "events": []}
            )
            events = tuple(state.get("events", []))
            audits, successful_results = self._persist_tool_events(
                investigation.session_id,
                events,
            )
            stop_reason = state.get("stop_reason")
            if stop_reason:
                raise InvestigationRunError(str(stop_reason))
            answer = self._extract_answer(state)
            output = self._parse_output(answer)
            self._memory.add_message(
                investigation.session_id,
                "assistant",
                answer,
            )
            evidence = self._persist_evidence(
                investigation,
                output,
                audits,
                successful_results,
            )
            evidence_by_key = {
                draft.key: item
                for draft, item in zip(output.evidence, evidence, strict=True)
            }
            report = self._tickets.save_diagnosis_report(
                investigation.id,
                category=output.report.category,
                suggested_priority=output.report.suggested_priority,
                root_cause=output.report.root_cause,
                confidence=output.report.confidence,
                evidence_ids=[
                    evidence_by_key[key].id
                    for key in output.report.evidence_keys
                ],
                recommended_actions=output.report.recommended_actions,
                reply_draft=output.report.reply_draft,
            )
            updated = self._tickets.mark_investigation_awaiting_review(
                investigation.id
            )
            self._tickets.transition_status(
                investigation.ticket_id,
                TicketStatus.AWAITING_REVIEW,
            )
            return InvestigationRunResult(
                investigation=updated,
                report=report,
                evidence=tuple(evidence),
                events=events,
            )
        except InvestigationRunError as exc:
            self._fail(investigation, exc.stop_reason)
            raise
        except (json.JSONDecodeError, ValidationError) as exc:
            self._fail(investigation, "invalid_diagnosis_report")
            raise InvestigationRunError("invalid_diagnosis_report") from exc
        except _EvidenceValidationError as exc:
            self._fail(investigation, "invalid_evidence")
            raise InvestigationRunError("invalid_evidence") from exc
        except Exception as exc:
            self._fail(investigation, "investigation_error")
            raise InvestigationRunError("investigation_error") from exc

    @staticmethod
    def _extract_answer(state: dict[str, Any]) -> str:
        messages = state.get("messages", [])
        if not messages or not isinstance(messages[-1], AIMessage):
            raise ValueError("investigation agent did not return an AI message")
        content = messages[-1].content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("investigation agent returned empty output")
        return content

    @staticmethod
    def _parse_output(answer: str) -> InvestigationOutput:
        stripped = answer.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        return InvestigationOutput.model_validate(json.loads(stripped))

    def _persist_tool_events(
        self,
        session_id: str,
        events: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, int], dict[str, dict[str, Any]]]:
        starts = {
            str(event["call_id"]): event
            for event in events
            if event.get("event") == "tool_start"
        }
        audits: dict[str, int] = {}
        successful_results: dict[str, dict[str, Any]] = {}
        for event in events:
            if event.get("event") not in {"tool_result", "tool_error"}:
                continue
            call_id = str(event["call_id"])
            start = starts.get(call_id, {})
            result = dict(event.get("result", {}))
            audit = self._memory.add_tool_audit(
                session_id,
                call_id,
                str(event.get("tool", start.get("tool", "unknown"))),
                dict(start.get("arguments", {})),
                result,
            )
            self._memory.add_message(
                session_id,
                "tool",
                json.dumps(result, ensure_ascii=False),
            )
            audits[call_id] = audit.id
            if event.get("event") == "tool_result" and result.get("success"):
                successful_results[call_id] = result
        return audits, successful_results

    def _persist_evidence(
        self,
        investigation: Investigation,
        output: InvestigationOutput,
        audits: dict[str, int],
        successful_results: dict[str, dict[str, Any]],
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        serialized_results = json.dumps(
            list(successful_results.values()),
            ensure_ascii=False,
        )
        attachment_ids = {
            attachment.id
            for attachment in self._tickets.list_attachments(
                investigation.ticket_id
            )
        }
        for draft in output.evidence:
            if draft.kind is EvidenceKind.TOOL_RESULT and (
                not draft.tool_call_id
                or draft.tool_call_id not in successful_results
                or draft.tool_call_id not in audits
            ):
                raise _EvidenceValidationError(
                    "tool evidence must cite a successful tool call"
                )
            if draft.kind is EvidenceKind.WEB_SOURCE and (
                not draft.source_ref
                or draft.source_ref not in serialized_results
            ):
                raise _EvidenceValidationError(
                    "web evidence URL must come from a successful tool call"
                )
            if draft.kind is EvidenceKind.ATTACHMENT and (
                not draft.source_ref
                or draft.attachment_id not in attachment_ids
            ):
                raise _EvidenceValidationError(
                    "attachment evidence must cite a ticket attachment location"
                )

        for draft in output.evidence:
            if draft.kind is EvidenceKind.TOOL_RESULT:
                item = self._tickets.add_evidence(
                    investigation.id,
                    kind=draft.kind,
                    title=draft.title,
                    summary=draft.summary,
                    tool_audit_id=audits[draft.tool_call_id],
                )
            elif draft.kind is EvidenceKind.WEB_SOURCE:
                item = self._tickets.add_evidence(
                    investigation.id,
                    kind=draft.kind,
                    title=draft.title,
                    summary=draft.summary,
                    source_ref=draft.source_ref,
                )
            elif draft.kind is EvidenceKind.ATTACHMENT:
                item = self._tickets.add_evidence(
                    investigation.id,
                    kind=draft.kind,
                    title=draft.title,
                    summary=draft.summary,
                    source_ref=draft.source_ref,
                    attachment_id=draft.attachment_id,
                )
            else:
                item = self._tickets.add_evidence(
                    investigation.id,
                    kind=draft.kind,
                    title=draft.title,
                    summary=draft.summary,
                )
            evidence.append(item)
        return evidence

    def _fail(
        self,
        investigation: Investigation,
        stop_reason: str,
    ) -> None:
        self._tickets.mark_investigation_failed(
            investigation.id,
            stop_reason=stop_reason,
        )
        ticket = self._tickets.get_ticket(investigation.ticket_id)
        if ticket.status is TicketStatus.INVESTIGATING:
            self._tickets.transition_status(ticket.id, TicketStatus.FAILED)
