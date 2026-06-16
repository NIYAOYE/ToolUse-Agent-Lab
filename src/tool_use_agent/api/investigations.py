from collections.abc import Iterator
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Query, status
from fastapi.responses import JSONResponse, StreamingResponse

from tool_use_agent.api.investigation_models import (
    DiagnosisTimeMetricsResponse,
    InvestigationDecisionRequest,
    InvestigationDecisionResponse,
    InvestigationDetailResponse,
    InvestigationResponse,
    InvestigationStartRequest,
)
from tool_use_agent.api.sse import encode_sse
from tool_use_agent.api.ticket_models import ApiErrorResponse
from tool_use_agent.investigations.models import InvestigationStatus
from tool_use_agent.investigations.service import (
    InvestigationService,
    InvalidApprovalDecision,
    InvalidInvestigationState,
)
from tool_use_agent.tickets.repository import ActiveInvestigationExists
from tool_use_agent.tickets.state_machine import InvalidTicketTransition


_TERMINAL_STREAM_STATUSES = {
    InvestigationStatus.AWAITING_REVIEW,
    InvestigationStatus.FAILED,
    InvestigationStatus.APPROVED,
}


def create_investigation_router(service: InvestigationService) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["investigations"])

    @router.post(
        "/tickets/{ticket_id}/investigations",
        response_model=InvestigationResponse,
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": ApiErrorResponse},
            status.HTTP_409_CONFLICT: {"model": ApiErrorResponse},
        },
    )
    def start_investigation(
        ticket_id: str,
        background_tasks: BackgroundTasks,
        request: InvestigationStartRequest | None = None,
    ):
        try:
            investigation = service.start(
                ticket_id,
                supplemental_instructions=(
                    request.supplemental_instructions if request else None
                ),
            )
        except KeyError:
            return _error_response(
                status.HTTP_404_NOT_FOUND,
                code="ticket_not_found",
                message=f"Ticket {ticket_id} was not found.",
                details={"ticket_id": ticket_id},
            )
        except ActiveInvestigationExists as exc:
            return _error_response(
                status.HTTP_409_CONFLICT,
                code=exc.code,
                message=str(exc),
                details={"ticket_id": ticket_id},
            )
        except InvalidTicketTransition as exc:
            return _error_response(
                status.HTTP_409_CONFLICT,
                code=exc.code,
                message=str(exc),
                details={"ticket_id": ticket_id},
            )
        background_tasks.add_task(service.run, investigation.id)
        return InvestigationResponse.model_validate(investigation)

    @router.get(
        "/investigations/{investigation_id}",
        response_model=InvestigationDetailResponse,
        responses={status.HTTP_404_NOT_FOUND: {"model": ApiErrorResponse}},
    )
    def get_investigation(investigation_id: int):
        try:
            detail = service.get_detail(investigation_id)
        except KeyError:
            return _investigation_not_found(investigation_id)
        return InvestigationDetailResponse.model_validate(detail)

    @router.get(
        "/investigations/{investigation_id}/events",
        responses={status.HTTP_404_NOT_FOUND: {"model": ApiErrorResponse}},
    )
    def stream_investigation_events(
        investigation_id: int,
        after_id: int = Query(default=0, ge=0),
    ):
        try:
            service.get_detail(investigation_id)
        except KeyError:
            return _investigation_not_found(investigation_id)

        def generate() -> Iterator[str]:
            cursor = after_id
            while True:
                events = service.list_events(
                    investigation_id,
                    after_id=cursor,
                )
                for item in events:
                    cursor = item.id
                    yield encode_sse(
                        item.event,
                        {
                            "id": item.id,
                            "investigation_id": item.investigation_id,
                            "created_at": item.created_at.isoformat(),
                            **item.payload,
                        },
                    )
                investigation = service.get_detail(
                    investigation_id
                ).investigation
                if (
                    investigation.status in _TERMINAL_STREAM_STATUSES
                    and not events
                ):
                    break
                time.sleep(0.05)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post(
        "/investigations/{investigation_id}/decision",
        response_model=InvestigationDecisionResponse,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": ApiErrorResponse},
            status.HTTP_409_CONFLICT: {"model": ApiErrorResponse},
        },
    )
    def decide_investigation(
        investigation_id: int,
        request: InvestigationDecisionRequest,
        background_tasks: BackgroundTasks,
    ):
        try:
            outcome = service.decide(
                investigation_id,
                decision=request.decision,
                final_draft=request.final_draft,
                review_notes=request.review_notes,
            )
        except KeyError:
            return _investigation_not_found(investigation_id)
        except (InvalidInvestigationState, InvalidApprovalDecision) as exc:
            return _error_response(
                status.HTTP_409_CONFLICT,
                code=exc.code,
                message=str(exc),
                details={"investigation_id": investigation_id},
            )
        if outcome.should_run:
            background_tasks.add_task(service.run, investigation_id)
        return InvestigationDecisionResponse(
            investigation=InvestigationResponse.model_validate(
                outcome.investigation
            ),
            approvals=tuple(outcome.approvals),
            should_run=outcome.should_run,
        )

    @router.get(
        "/metrics/diagnosis-time",
        response_model=DiagnosisTimeMetricsResponse,
    )
    def get_diagnosis_time_metrics() -> DiagnosisTimeMetricsResponse:
        return DiagnosisTimeMetricsResponse.model_validate(
            service.get_diagnosis_time_metrics()
        )

    return router


def _investigation_not_found(investigation_id: int) -> JSONResponse:
    return _error_response(
        status.HTTP_404_NOT_FOUND,
        code="investigation_not_found",
        message=f"Investigation {investigation_id} was not found.",
        details={"investigation_id": investigation_id},
    )


def _error_response(
    status_code: int,
    *,
    code: str,
    message: str,
    details: dict[str, Any],
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "request_id": str(uuid4()),
            "details": details,
        },
    )
