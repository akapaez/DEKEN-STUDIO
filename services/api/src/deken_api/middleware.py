"""Middleware ASGI: identificador de petición, log de acceso, cabeceras de seguridad y
límite de tamaño del cuerpo."""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from deken_api.logs import get_logger

log = get_logger("deken_api.access")

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (b"cache-control", b"no-store"),
]
API_CSP = b"default-src 'none'; frame-ancestors 'none'"
DOCS_CSP = (
    b"default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    b"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: "
    b"https://fastapi.tiangolo.com; frame-ancestors 'none'"
)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        incoming = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _REQUEST_ID_RE.fullmatch(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        path: str = scope.get("path", "")
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_holder: dict[str, Any] = {"status": 500}
        is_docs = path.startswith(("/api/docs", "/api/redoc"))

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                extra = [
                    (b"x-request-id", request_id.encode()),
                    *SECURITY_HEADERS,
                    (b"content-security-policy", DOCS_CSP if is_docs else API_CSP),
                ]
                if self.hsts:
                    extra.append((b"strict-transport-security", b"max-age=63072000"))
                existing = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = [
                    *message.get("headers", []),
                    *[(k, v) for k, v in extra if k not in existing],
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if not path.startswith("/api/v1/health"):
                log.info(
                    "http.request",
                    method=scope.get("method"),
                    path=path,
                    status=status_holder["status"],
                    duration_ms=round((time.perf_counter() - started) * 1000, 1),
                    client=(scope.get("client") or ("-",))[0],
                )


class BodySizeLimitMiddleware:
    """Rechaza cuerpos mayores que `max_bytes` (también los enviados por chunks)."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await _reject(send)
            return
        received = 0
        too_large = False
        rejected = False

        async def limited_receive() -> Message:
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    too_large = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Message) -> None:
            # Si el cuerpo era demasiado grande, la respuesta de la app (un 400/500 por el
            # error de lectura) se sustituye por un 413 explícito.
            nonlocal rejected
            if too_large:
                if not rejected:
                    rejected = True
                    await _reject(send)
                return
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            if not rejected:
                await _reject(send)


class _BodyTooLarge(Exception):
    pass


async def _reject(send: Send) -> None:
    body = b'{"error":{"code":"payload_too_large","message":"Cuerpo demasiado grande"}}'
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
