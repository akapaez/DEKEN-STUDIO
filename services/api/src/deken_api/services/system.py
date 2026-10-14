"""Comprobaciones de salud y estado del sistema."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api import __version__
from deken_api.context import AppContext
from deken_api.integrations.ffprobe import ffprobe_version
from deken_api.services.jobs import JobService
from deken_api.services.workers import is_online, list_workers

CHECK_TIMEOUT_SECONDS = 3.0


async def _timed(check: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        detail = await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS)
    except Exception as exc:
        return {"status": "error", "error": type(exc).__name__}
    result: dict[str, Any] = {
        "status": "ok",
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    }
    if isinstance(detail, dict):
        result.update(detail)
    return result


async def readiness(app: AppContext) -> dict[str, dict[str, Any]]:
    async def db_check() -> dict[str, Any]:
        async with app.engine.connect() as conn:
            revision = (
                await conn.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one_or_none()
        return {"migration": revision}

    async def redis_check() -> None:
        await app.redis.ping()

    async def storage_check() -> dict[str, Any]:
        await app.storage.health()
        return {"bucket": app.storage.bucket}

    db, redis, storage = await asyncio.gather(
        _timed(db_check), _timed(redis_check), _timed(storage_check)
    )
    return {"database": db, "redis": redis, "storage": storage}


OverallStatus = Literal["ok", "degraded", "error"]


def overall_status(checks: dict[str, dict[str, Any]]) -> OverallStatus:
    """`error` si falla BD o almacenamiento; `degraded` si solo falla Redis (hay
    alternativas: sondeo de BD y limitador en memoria)."""
    if checks["database"]["status"] != "ok" or checks["storage"]["status"] != "ok":
        return "error"
    if checks["redis"]["status"] != "ok":
        return "degraded"
    return "ok"


async def status(db: AsyncSession, app: AppContext) -> dict[str, Any]:
    checks = await readiness(app)
    settings = app.settings
    now = datetime.now(UTC)
    workers = await list_workers(db)
    online = [w for w in workers if is_online(w, threshold_seconds=settings.worker_online_seconds)]
    jobs = JobService(db, app)
    ffprobe = await ffprobe_version(settings.ffprobe_path)
    return {
        "status": overall_status(checks),
        "version": __version__,
        "environment": settings.environment.value,
        "server_time": now,
        "checks": checks,
        "ffprobe": {"available": ffprobe is not None, "version": ffprobe},
        "workers": {
            "active": sum(1 for w in workers if w.status == "active"),
            "online": len(online),
            "online_names": [w.name for w in online],
        },
        "jobs": {
            "by_status": await jobs.counts(),
            "failed_last_24h": await jobs.failed_since(now - timedelta(hours=24)),
        },
        "ai": {
            "configured": settings.ai_configured,
            "provider": settings.ai_provider if settings.ai_configured else None,
        },
    }
