"""Dependencias de FastAPI: BD, sesión de usuario, permisos, worker y CSRF."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.config import Settings
from deken_api.context import AppContext
from deken_api.db.models import User, UserSession, Worker
from deken_api.errors import ApiError, NotAuthenticated, PermissionDenied
from deken_api.security.rbac import Permission, Role, permissions_for
from deken_api.security.tokens import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    constant_time_equals,
    csrf_token_for,
)
from deken_api.services import audit
from deken_api.services.audit import Actor, AuditContext, RequestMeta
from deken_api.services.auth import resolve_session, user_actor
from deken_api.services.workers import authenticate_worker
from deken_shared.jobs import CONTRACT_HEADER, JOB_CONTRACT_VERSION

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def get_ctx(request: Request) -> AppContext:
    ctx: AppContext = request.app.state.ctx
    return ctx


Ctx = Annotated[AppContext, Depends(get_ctx)]


async def get_db(ctx: Ctx) -> AsyncIterator[AsyncSession]:
    async with ctx.sessionmaker() as session:
        yield session


Db = Annotated[AsyncSession, Depends(get_db)]


def get_meta(request: Request) -> RequestMeta:
    return RequestMeta(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
    )


Meta = Annotated[RequestMeta, Depends(get_meta)]


def check_origin(request: Request, settings: Settings) -> None:
    """Rechaza peticiones no seguras desde orígenes no permitidos."""
    if request.method in SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin is not None and origin.rstrip("/") not in settings.allowed_origins:
        raise PermissionDenied("Origen no permitido", code="origin_not_allowed")


def check_csrf(request: Request, session: UserSession, settings: Settings) -> None:
    if request.method in SAFE_METHODS:
        return
    check_origin(request, settings)
    provided = request.headers.get(CSRF_HEADER, "")
    expected = csrf_token_for(session.id, settings.secret_key.get_secret_value())
    if not provided or not constant_time_equals(provided, expected):
        raise PermissionDenied("Token CSRF ausente o no válido", code="csrf_failed")


@dataclass(frozen=True)
class Principal:
    session: UserSession
    user: User
    role: Role
    permissions: frozenset[Permission]
    meta: RequestMeta

    @property
    def audit(self) -> AuditContext:
        return AuditContext(user_actor(self.user), self.meta)


async def current_principal(request: Request, db: Db, ctx: Ctx, meta: Meta) -> Principal:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise NotAuthenticated("Inicia sesión para continuar")
    session = await resolve_session(db, token, settings=ctx.settings)
    if session is None:
        raise NotAuthenticated("La sesión ha caducado o no es válida", code="session_invalid")
    check_csrf(request, session, ctx.settings)
    role = Role(session.user.role)
    return Principal(
        session=session,
        user=session.user,
        role=role,
        permissions=permissions_for(role),
        meta=meta,
    )


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]


def require(permission: Permission) -> Any:
    async def _dep(principal: CurrentPrincipal, db: Db, request: Request) -> Principal:
        if permission not in principal.permissions:
            audit.record(
                db,
                principal.audit,
                "authz.denied",
                outcome="denied",
                details={
                    "permission": permission.value,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            await db.commit()
            raise PermissionDenied("No tienes permiso para esta acción")
        return principal

    return Depends(_dep)


def set_session_cookies(
    response: Response, *, token: str, session: UserSession, settings: Settings
) -> str:
    max_age = settings.session_absolute_hours * 3600
    csrf = csrf_token_for(session.id, settings.secret_key.get_secret_value())
    common = {"max_age": max_age, "secure": settings.secure_cookies, "path": "/"}
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", **common)  # type: ignore[arg-type]
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="lax", **common)  # type: ignore[arg-type]
    return csrf


def clear_session_cookies(response: Response, settings: Settings) -> None:
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", secure=settings.secure_cookies, samesite="lax")


async def current_worker(request: Request, db: Db) -> Worker:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise NotAuthenticated("Token de worker requerido", headers={"WWW-Authenticate": "Bearer"})
    worker = await authenticate_worker(db, token.strip())
    if worker is None:
        audit.record(
            db,
            AuditContext(Actor.anonymous(), get_meta(request)),
            "worker.auth",
            outcome="failure",
        )
        await db.commit()
        raise NotAuthenticated(
            "Token de worker no válido o revocado", headers={"WWW-Authenticate": "Bearer"}
        )
    version = request.headers.get(CONTRACT_HEADER)
    if version != str(JOB_CONTRACT_VERSION):
        raise ApiError(
            f"Versión de contrato no soportada: se requiere {JOB_CONTRACT_VERSION}",
            code="contract_version_unsupported",
            status_code=400,
        )
    return worker


CurrentWorker = Annotated[Worker, Depends(current_worker)]
