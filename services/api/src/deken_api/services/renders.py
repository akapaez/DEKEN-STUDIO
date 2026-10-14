"""Renders con Remotion: evaluación técnica y líneas de tiempo `deken.timeline/1`.

Puerta de licencia (ADR 0005): mientras DEKEN no verifique la licencia de empresa de
Remotion (`DEKEN_REMOTION_LICENSE_MODE=evaluation`), solo se aceptan renders de
evaluación, que salen con marca de agua y se guardan aparte (`evaluation/`).
"""

from __future__ import annotations

import json
import uuid
from functools import lru_cache
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.context import AppContext
from deken_api.db.models import BrandAsset, Job, MediaAsset, StoredObject
from deken_api.errors import ApiError, Conflict
from deken_api.services.audit import AuditContext
from deken_api.services.jobs import JobService
from deken_api.services.media import extension_of, usable_for_production
from deken_shared.jobs import InputRef, JobType, RemotionEvalPayload, RenderTimelinePayload

MAX_ISSUES = 50
MAX_TIMELINE_SECONDS = 10 * 60  # igual que MAX_DURATION_SECONDS en timeline.ts


@lru_cache(maxsize=1)
def timeline_validator() -> Draft202012Validator:
    text = (
        resources.files("deken_shared").joinpath("schemas/timeline.schema.json").read_text("utf-8")
    )
    return Draft202012Validator(json.loads(text))


def schema_issues(timeline: dict[str, Any]) -> list[dict[str, str]]:
    errors = sorted(timeline_validator().iter_errors(timeline), key=lambda e: list(e.absolute_path))
    return [
        {"path": ".".join(str(p) for p in e.absolute_path) or "(raíz)", "message": e.message[:300]}
        for e in errors[:MAX_ISSUES]
    ]


def referenced_ids(timeline: dict[str, Any]) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
    assets: set[uuid.UUID] = set()
    brand: set[uuid.UUID] = set()
    for track in timeline.get("tracks", []):
        for clip in track.get("clips", []):
            if clip.get("asset_id"):
                assets.add(uuid.UUID(str(clip["asset_id"])))
            if clip.get("brand_asset_id"):
                brand.add(uuid.UUID(str(clip["brand_asset_id"])))
    return assets, brand


class RenderService:
    def __init__(self, db: AsyncSession, app: AppContext) -> None:
        self.db = db
        self.app = app
        self.settings = app.settings

    @property
    def commercial_enabled(self) -> bool:
        return self.settings.remotion_license_mode == "company"

    async def create_evaluation(self, ctx: AuditContext, payload: RemotionEvalPayload) -> Job:
        return await JobService(self.db, self.app).create(
            JobType.SYSTEM_REMOTION_EVAL.value, payload.model_dump(mode="json"), ctx=ctx
        )

    async def create_timeline_render(
        self, ctx: AuditContext, *, timeline: dict[str, Any], purpose: str, title: str | None
    ) -> Job:
        if purpose == "production" and not self.commercial_enabled:
            raise Conflict(
                "Los renders de producción con Remotion están deshabilitados hasta verificar "
                "la licencia de empresa. Usa el propósito 'evaluation'.",
                code="remotion_license_required",
            )
        issues = schema_issues(timeline)
        if issues:
            raise ApiError(
                "La línea de tiempo no cumple el esquema deken.timeline/1",
                code="invalid_timeline",
                status_code=422,
                details=issues,
            )
        output = timeline["output"]
        if output["duration_frames"] > MAX_TIMELINE_SECONDS * output["fps"]:
            raise ApiError(
                "La línea de tiempo supera la duración máxima",
                code="invalid_timeline",
                status_code=422,
                details=[{"path": "output.duration_frames", "message": "duración máxima superada"}],
            )
        inputs = await self._resolve(timeline, purpose)
        payload = RenderTimelinePayload.model_validate(
            {"timeline": timeline, "purpose": purpose, "inputs": inputs, "title": title}
        )
        return await JobService(self.db, self.app).create(
            JobType.RENDER_TIMELINE.value, payload.model_dump(mode="json"), ctx=ctx
        )

    async def _resolve(self, timeline: dict[str, Any], purpose: str) -> list[InputRef]:
        """Comprueba que cada medio referenciado existe y está autorizado para el uso."""
        asset_ids, brand_ids = referenced_ids(timeline)
        problems: list[dict[str, str]] = []
        inputs: list[InputRef] = []
        assets = {
            a.id: a
            for a in (
                await self.db.execute(select(MediaAsset).where(MediaAsset.id.in_(asset_ids)))
            ).scalars()
        }
        for asset_id in sorted(asset_ids, key=str):
            asset = assets.get(asset_id)
            if asset is None or asset.status != "ready" or asset.archived_at is not None:
                problems.append(
                    {"path": f"asset:{asset_id}", "message": "medio inexistente o no disponible"}
                )
                continue
            if purpose == "production" and not usable_for_production(asset):
                problems.append(
                    {
                        "path": f"asset:{asset_id}",
                        "message": "derechos de imagen no autorizados para producción",
                    }
                )
                continue
            original = await self.db.get(StoredObject, asset.original_object_id)
            if original is None or original.status != "available":
                problems.append({"path": f"asset:{asset_id}", "message": "original no disponible"})
                continue
            inputs.append(
                InputRef(
                    name=f"asset-{asset_id}",
                    object_id=original.id,
                    kind="video",
                    extension=extension_of(asset.original_filename) or "mp4",
                    key=f"asset:{asset_id}",
                    width=asset.width,
                    height=asset.height,
                    duration_s=asset.duration_s,
                    has_audio=asset.has_audio,
                )
            )
        brands = {
            b.id: b
            for b in (
                await self.db.execute(select(BrandAsset).where(BrandAsset.id.in_(brand_ids)))
            ).scalars()
        }
        for brand_id in sorted(brand_ids, key=str):
            brand = brands.get(brand_id)
            if (
                brand is None
                or brand.status != "ready"
                or brand.archived_at is not None
                or brand.kind == "font"
            ):
                problems.append(
                    {"path": f"brand:{brand_id}", "message": "recurso de marca no disponible"}
                )
                continue
            obj = await self.db.get(StoredObject, brand.object_id)
            if obj is None or obj.status != "available":
                problems.append(
                    {"path": f"brand:{brand_id}", "message": "fichero de marca no disponible"}
                )
                continue
            inputs.append(
                InputRef(
                    name=f"brand-{brand_id}",
                    object_id=obj.id,
                    kind="image",
                    extension=extension_of(brand.original_filename) or "png",
                    key=f"brand:{brand_id}",
                    width=brand.width,
                    height=brand.height,
                )
            )
        if problems:
            raise ApiError(
                "La línea de tiempo referencia medios no autorizados",
                code="unauthorized_media",
                status_code=422,
                details=problems,
            )
        return inputs
