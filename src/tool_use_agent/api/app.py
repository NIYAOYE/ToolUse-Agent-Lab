from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse

from tool_use_agent.api.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    MessageResponse,
    SessionResponse,
)
from tool_use_agent.api.sse import encode_sse
from tool_use_agent.api.investigations import create_investigation_router
from tool_use_agent.api.tickets import create_ticket_router
from tool_use_agent.investigations.service import InvestigationService
from tool_use_agent.service import ChatService
from tool_use_agent.tickets.service import TicketService


def create_app(
    service: ChatService,
    ticket_service: TicketService | None = None,
    investigation_service: InvestigationService | None = None,
) -> FastAPI:
    app = FastAPI(title="ToolUse Agent Lab", version="0.1.0")

    if ticket_service is not None:
        app.include_router(create_ticket_router(ticket_service))
    if investigation_service is not None:
        app.include_router(
            create_investigation_router(investigation_service)
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post(
        "/v1/sessions",
        response_model=SessionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_session() -> SessionResponse:
        return SessionResponse.model_validate(service.create_session())

    @app.get("/v1/sessions/{session_id}", response_model=SessionResponse)
    def get_session(session_id: str) -> SessionResponse:
        try:
            session = service.get_session(session_id)
        except KeyError as exc:
            raise _not_found() from exc
        return SessionResponse.model_validate(session)

    @app.get(
        "/v1/sessions/{session_id}/messages",
        response_model=list[MessageResponse],
    )
    def list_messages(session_id: str) -> list[MessageResponse]:
        try:
            messages = service.list_messages(session_id)
        except KeyError as exc:
            raise _not_found() from exc
        return [MessageResponse.model_validate(item) for item in messages]

    @app.post("/v1/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        try:
            result = service.chat(request.session_id, request.message)
        except KeyError as exc:
            raise _not_found() from exc
        return ChatResponse(
            session_id=result.session_id,
            request_id=result.request_id,
            answer=result.answer,
            tool_steps=result.tool_steps,
            stop_reason=result.stop_reason,
        )

    @app.post("/v1/chat/stream")
    def stream_chat(request: ChatRequest) -> StreamingResponse:
        try:
            service.get_session(request.session_id)
        except KeyError as exc:
            raise _not_found() from exc

        def generate() -> Iterator[str]:
            try:
                for item in service.stream_chat(
                    request.session_id,
                    request.message,
                ):
                    event = item["event"]
                    payload: dict[str, Any] = {
                        key: value for key, value in item.items() if key != "event"
                    }
                    yield encode_sse(event, payload)
            except Exception:
                yield encode_sse(
                    "error",
                    {
                        "session_id": request.session_id,
                        "code": "stream_error",
                        "message": "Chat stream failed unexpectedly.",
                    },
                )

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="session_not_found",
    )
