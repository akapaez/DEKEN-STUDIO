"""Punto de entrada de la API: `uvicorn deken_api.main:app`."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from deken_api import __version__
from deken_api.api.v1.router import API_PREFIX, router
from deken_api.config import Environment, Settings, get_settings
from deken_api.context import AppContext
from deken_api.errors import install_error_handlers
from deken_api.logs import configure_logging, get_logger
from deken_api.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from deken_api.services.jobs import JobService

log = get_logger(__name__)


async def _reaper_loop(ctx: AppContext) -> None:
    """Devuelve a la cola los trabajos de workers que han dejado de responder."""
    interval = ctx.settings.job_reaper_interval_seconds
    while True:
        try:
            async with ctx.sessionmaker() as db:
                reaped = await JobService(db, ctx).reap_expired()
            if reaped:
                log.info("jobs.reaped", count=reaped)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("jobs.reaper_error")
        await asyncio.sleep(interval)


def _operation_id(route: APIRoute) -> str:
    return route.name


def create_app(settings: Settings | None = None, *, run_reaper: bool = True) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ctx = AppContext.create(settings)
        app.state.ctx = ctx
        reaper = asyncio.create_task(_reaper_loop(ctx)) if run_reaper else None
        log.info("api.started", version=__version__, environment=settings.environment.value)
        try:
            yield
        finally:
            if reaper is not None:
                reaper.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await reaper
            await ctx.close()

    show_docs = settings.environment is not Environment.PRODUCTION
    app = FastAPI(
        title="DEKEN STUDIO AI — API",
        version=__version__,
        description="API v1 de DEKEN STUDIO AI. Ver docs/CONTRACTS.md.",
        lifespan=lifespan,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url="/api/docs" if show_docs else None,
        redoc_url=None,
        generate_unique_id_function=_operation_id,
    )
    install_error_handlers(app)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(RequestContextMiddleware, hsts=settings.secure_cookies)
    app.include_router(router)
    return app


def __getattr__(name: str) -> FastAPI:
    # `uvicorn deken_api.main:app` crea la app al importarla, no en tests.
    if name == "app":
        return create_app()
    raise AttributeError(name)
