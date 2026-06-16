from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, File, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse

from tool_use_agent.api.ticket_models import (
    ApiErrorResponse,
    AttachmentResponse,
    TicketCreateRequest,
    TicketDetailResponse,
    TicketPageResponse,
    TicketResponse,
    TicketImportResponse,
)
from tool_use_agent.tickets.models import TicketPriority, TicketStatus
from tool_use_agent.tickets.repository import TicketAlreadyExists
from tool_use_agent.tickets.service import (
    AttachmentTooLarge,
    AttachmentValidationError,
    TicketImportTooLarge,
    TicketImportValidationError,
    TicketService,
)


def create_ticket_router(service: TicketService) -> APIRouter:
    router = APIRouter(prefix="/v1/tickets", tags=["tickets"])

    @router.post(
        "",
        response_model=TicketResponse,
        status_code=status.HTTP_201_CREATED,
        responses={status.HTTP_409_CONFLICT: {"model": ApiErrorResponse}},
    )
    def create_ticket(request: TicketCreateRequest):
        try:
            ticket = service.create_ticket(
                ticket_id=request.id,
                title=request.title,
                description=request.description,
                environment=request.environment,
                service=request.service,
                priority=request.priority,
                category=request.category,
            )
        except TicketAlreadyExists as exc:
            return _error_response(
                status.HTTP_409_CONFLICT,
                code=exc.code,
                message=str(exc),
                details={"ticket_id": exc.ticket_id},
            )
        return TicketResponse.model_validate(ticket)

    @router.get("", response_model=TicketPageResponse)
    def list_tickets(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status_filter: TicketStatus | None = Query(default=None, alias="status"),
        priority: TicketPriority | None = None,
        sort_by: Literal["created_at", "updated_at", "priority"] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> TicketPageResponse:
        result = service.list_tickets(
            page=page,
            page_size=page_size,
            status=status_filter,
            priority=priority,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return TicketPageResponse(
            items=[TicketResponse.model_validate(item) for item in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    @router.post(
        "/import",
        response_model=TicketImportResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_400_BAD_REQUEST: {"model": ApiErrorResponse},
            status.HTTP_413_CONTENT_TOO_LARGE: {"model": ApiErrorResponse},
        },
    )
    async def import_tickets(file: UploadFile = File(...)):
        content = await file.read(service.max_import_bytes + 1)
        filename = file.filename or ""
        try:
            tickets = service.import_tickets(filename, content)
        except TicketImportValidationError as exc:
            return _error_response(
                status.HTTP_400_BAD_REQUEST,
                code=exc.code,
                message=str(exc),
                details={"errors": exc.errors},
            )
        except TicketImportTooLarge as exc:
            return _error_response(
                status.HTTP_413_CONTENT_TOO_LARGE,
                code=exc.code,
                message=str(exc),
                details={"max_bytes": service.max_import_bytes},
            )
        return TicketImportResponse(
            imported_count=len(tickets),
            tickets=[TicketResponse.model_validate(item) for item in tickets],
        )

    @router.get(
        "/{ticket_id}",
        response_model=TicketDetailResponse,
        responses={status.HTTP_404_NOT_FOUND: {"model": ApiErrorResponse}},
    )
    def get_ticket(ticket_id: str):
        try:
            detail = service.get_ticket_detail(ticket_id)
        except KeyError:
            return _error_response(
                status.HTTP_404_NOT_FOUND,
                code="ticket_not_found",
                message=f"Ticket {ticket_id} was not found.",
                details={"ticket_id": ticket_id},
            )
        return TicketDetailResponse.model_validate(detail)

    @router.delete(
        "/{ticket_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={status.HTTP_404_NOT_FOUND: {"model": ApiErrorResponse}},
    )
    def delete_ticket(ticket_id: str):
        try:
            service.delete_ticket(ticket_id)
        except KeyError:
            return _error_response(
                status.HTTP_404_NOT_FOUND,
                code="ticket_not_found",
                message=f"Ticket {ticket_id} was not found.",
                details={"ticket_id": ticket_id},
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/{ticket_id}/attachments",
        response_model=AttachmentResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_400_BAD_REQUEST: {"model": ApiErrorResponse},
            status.HTTP_404_NOT_FOUND: {"model": ApiErrorResponse},
            status.HTTP_413_CONTENT_TOO_LARGE: {"model": ApiErrorResponse},
        },
    )
    async def upload_attachment(ticket_id: str, file: UploadFile = File(...)):
        content = await file.read(service.max_attachment_bytes + 1)
        try:
            attachment = service.save_attachment(
                ticket_id,
                filename=file.filename or "",
                media_type=file.content_type or "application/octet-stream",
                content=content,
            )
        except KeyError:
            return _error_response(
                status.HTTP_404_NOT_FOUND,
                code="ticket_not_found",
                message=f"Ticket {ticket_id} was not found.",
                details={"ticket_id": ticket_id},
            )
        except AttachmentValidationError as exc:
            return _error_response(
                status.HTTP_400_BAD_REQUEST,
                code=exc.code,
                message=str(exc),
                details={},
            )
        except AttachmentTooLarge as exc:
            return _error_response(
                status.HTTP_413_CONTENT_TOO_LARGE,
                code=exc.code,
                message=str(exc),
                details={"max_bytes": service.max_attachment_bytes},
            )
        return AttachmentResponse.model_validate(attachment)

    return router


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
