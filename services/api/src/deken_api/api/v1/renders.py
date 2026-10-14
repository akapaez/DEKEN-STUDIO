"""Renders con Remotion (evaluación técnica y líneas de tiempo)."""

from __future__ import annotations

from fastapi import APIRouter, status

from deken_api.api.v1.schemas import (
    JobOut,
    RemotionEvalRequest,
    RenderEngineOut,
    TimelineRenderRequest,
)
from deken_api.deps import Ctx, Db, Principal, require
from deken_api.security.rbac import Permission
from deken_api.services.renders import RenderService
from deken_api.services.workers import is_online, list_workers
from deken_shared.jobs import JobType, RemotionEvalPayload

router = APIRouter(prefix="/renders", tags=["renders"])


@router.get("/engine", response_model=RenderEngineOut)
async def render_engine(
    db: Db, ctx: Ctx, _: Principal = require(Permission.SYSTEM_READ)
) -> RenderEngineOut:
    workers = [
        w.name
        for w in await list_workers(db)
        if is_online(w, threshold_seconds=ctx.settings.worker_online_seconds)
        and JobType.SYSTEM_REMOTION_EVAL.value in (w.capabilities or {}).get("job_types", [])
    ]
    commercial = ctx.settings.remotion_license_mode == "company"
    return RenderEngineOut(
        engine="remotion",
        license_mode=ctx.settings.remotion_license_mode,
        commercial_renders_enabled=commercial,
        workers_with_remotion=workers,
        note=(
            "Licencia de empresa de Remotion verificada: renders de producción habilitados."
            if commercial
            else "Licencia comercial de Remotion pendiente de verificar por Grupo Deken: solo "
            "renders de evaluación (con marca de agua), separados del contenido comercial."
        ),
    )


@router.post("/evaluation", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation_render(
    body: RemotionEvalRequest,
    db: Db,
    ctx: Ctx,
    principal: Principal = require(Permission.SYSTEM_MANAGE),
) -> JobOut:
    """Encola la composición de evaluación técnica (5 s, 1080×1920, 30 fps)."""
    payload = RemotionEvalPayload(title=body.title, subtitle=body.subtitle)
    job = await RenderService(db, ctx).create_evaluation(principal.audit, payload)
    return JobOut.model_validate(job)


@router.post("/timeline", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_timeline_render(
    body: TimelineRenderRequest,
    db: Db,
    ctx: Ctx,
    principal: Principal = require(Permission.RENDER_CREATE),
) -> JobOut:
    job = await RenderService(db, ctx).create_timeline_render(
        principal.audit, timeline=body.timeline, purpose=body.purpose, title=body.title
    )
    return JobOut.model_validate(job)
