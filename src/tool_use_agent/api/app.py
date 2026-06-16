from collections.abc import Iterator
import json
import logging
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request

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


_REQUEST_LOGGER = logging.getLogger(
    "uvicorn.error.tool_use_agent.api.requests"
)
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+\Z")


def create_app(
    service: ChatService,
    ticket_service: TicketService | None = None,
    investigation_service: InvestigationService | None = None,
    *,
    allowed_hosts: tuple[str, ...] = (
        "127.0.0.1",
        "localhost",
        "testserver",
    ),
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ),
) -> FastAPI:
    app = FastAPI(title="ToolUse Agent Lab", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(allowed_hosts),
    )

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = _request_id(request.headers.get("x-request-id"))
        started = perf_counter()
        response = await call_next(request)
        duration_ms = round((perf_counter() - started) * 1000, 3)
        response.headers["X-Request-ID"] = request_id
        _REQUEST_LOGGER.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return response

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


def _request_id(value: str | None) -> str:
    if value and len(value) <= 128 and _REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid4())
