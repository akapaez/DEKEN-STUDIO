from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from deken_api.api.v1.schemas import HealthOut, JobOut, SelftestRequest, SystemStatusOut
from deken_api.deps import Ctx, Db, Principal, require
from deken_api.security.rbac import Permission
from deken_api.services import system as system_service
from deken_api.services.jobs import JobService
from deken_shared.jobs import JobType, RenderSelftestPayload

router = APIRouter(tags=["system"])


@router.get("/health/live", response_model=HealthOut)
async def live() -> HealthOut:
    """El proceso responde. No comprueba dependencias."""
    return HealthOut(status="ok", checks={})


@router.get(
    "/health/ready",
    response_model=HealthOut,
    responses={503: {"model": HealthOut, "description": "Dependencia crítica caída"}},
)
async def ready(ctx: Ctx) -> JSONResponse:
    """Disponibilidad. 503 si fallan BD o almacenamiento; `degraded` si solo falla Redis."""
    checks = await system_service.readiness(ctx)
    overall = system_service.overall_status(checks)
    body = HealthOut(status=overall, checks={k: v["status"] for k, v in checks.items()})
    code = status.HTTP_503_SERVICE_UNAVAILABLE if overall == "error" else status.HTTP_200_OK
    return JSONResponse(body.model_dump(), status_code=code)


@router.get("/system/status", response_model=SystemStatusOut)
async def system_status(
    db: Db, ctx: Ctx, _: Principal = require(Permission.SYSTEM_READ)
) -> SystemStatusOut:
    return SystemStatusOut.model_validate(await system_service.status(db, ctx))


@router.post("/system/selftest", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def render_selftest(
    body: SelftestRequest,
    db: Db,
    ctx: Ctx,
    principal: Principal = require(Permission.SYSTEM_MANAGE),
) -> JobOut:
    """Encola un autotest de render con señal SINTÉTICA (no es contenido de DEKEN)."""
    payload = RenderSelftestPayload(duration_s=body.duration_s)
    job = await JobService(db, ctx).create(
        JobType.SYSTEM_RENDER_SELFTEST.value,
        payload.model_dump(mode="json"),
        ctx=principal.audit,
    )
    return JobOut.model_validate(job)
