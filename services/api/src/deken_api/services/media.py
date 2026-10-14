"""Biblioteca audiovisual: importación de originales MP4/MOV y su catalogación.

Flujo:
1. `create_upload`: valida nombre/tipo/tamaño, reserva una clave inmutable y abre una
   subida multiparte S3. El navegador sube las partes con URLs firmadas.
2. `complete_upload`: la API cierra la subida (con los ETag que lista S3, no los que
   diga el cliente), comprueba el tamaño y analiza el fichero con ffprobe en el servidor.
   Si no es un vídeo válido se rechaza y se elimina; si lo es, se encola `media.ingest`.
3. `media.ingest` (worker): SHA-256, decodificación de muestra, póster, tira, proxy y
   forma de onda. Al completarse, `ingest_finished` detecta duplicados por SHA-256.

El original nunca se modifica ni se sobrescribe: la clave se genera una sola vez y no
existe ninguna operación que vuelva a escribirla.
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.context import AppContext
from deken_api.db.models import Job, JobOutput, MediaAsset, StoredObject
from deken_api.errors import ApiError, Conflict, NotFound
from deken_api.integrations.ffprobe import ProbeError, probe_url
from deken_api.integrations.storage import Audience, StorageError, build_object_key
from deken_api.logs import get_logger
from deken_api.services import audit
from deken_api.services.audit import AuditContext
from deken_api.services.jobs import JobService
from deken_shared.jobs import InputRef, JobStatus, JobType, MediaIngestPayload, ProxyTarget
from deken_shared.media import ProbeSummary

log = get_logger(__name__)

ALLOWED_EXTENSIONS = {"mp4": "video/mp4", "mov": "video/quicktime"}
ACCEPTED_CONTENT_TYPES = {"video/mp4", "video/quicktime", "application/octet-stream", ""}
VIDEO_CONTAINERS = {"mov", "mp4"}
PROXY_SHORT_SIDE = 540
STANDARD_RATES = (23.976, 24.0, 25.0, 29.97, 30.0, 48.0, 50.0, 59.94, 60.0)
MAX_TAGS = 30
TAG_RE = re.compile(r"^[\wáéíóúüñ][\wáéíóúüñ .-]{0,47}$", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(UTC)


def extension_of(filename: str) -> str:
    return PurePosixPath(filename.replace("\\", "/")).suffix.lower().lstrip(".")


def normalize_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in tags:
        tag = " ".join(raw.strip().lower().split())
        if not tag:
            continue
        if not TAG_RE.fullmatch(tag):
            raise ApiError(f"Etiqueta no válida: {raw!r}", code="invalid_tag", status_code=422)
        if tag not in cleaned:
            cleaned.append(tag)
    if len(cleaned) > MAX_TAGS:
        raise ApiError(f"Máximo {MAX_TAGS} etiquetas", code="too_many_tags", status_code=422)
    return cleaned


def snap_fps(fps: float | None) -> float:
    """Cadencia del proxy: la estándar más cercana (≤ 0,5 %) o redondeada; nunca > 60."""
    if not fps or fps <= 0:
        return 30.0
    fps = min(fps, 60.0)
    nearest = min(STANDARD_RATES, key=lambda rate: abs(fps - rate) / rate)
    if abs(fps - nearest) / nearest <= 0.005:
        return nearest
    return round(fps, 2)


def proxy_size(width: int, height: int) -> tuple[int, int]:
    """Proxy con el lado corto a 540 px (sin ampliar), conservando la proporción."""
    scale = min(1.0, PROXY_SHORT_SIDE / min(width, height))

    def even(v: float) -> int:
        return max(16, round(v / 2) * 2)

    return even(width * scale), even(height * scale)


@dataclass(frozen=True)
class UploadPlan:
    asset: MediaAsset
    part_size: int
    part_count: int


@dataclass(frozen=True)
class PartUrl:
    part_number: int
    url: str


def orientation_of(width: int | None, height: int | None) -> str | None:
    if not width or not height:
        return None
    ratio = width / height
    if abs(ratio - 1) < 0.05:
        return "square"
    return "horizontal" if ratio > 1 else "vertical"


def usable_for_production(asset: MediaAsset) -> bool:
    """Un activo se puede montar si está listo y sus derechos de imagen lo permiten."""
    if asset.status != "ready" or asset.archived_at is not None:
        return False
    if asset.consent_status == "denied":
        return False
    if asset.people_present == "no":
        return True
    return asset.consent_status in {"granted", "not_required"}


class MediaService:
    def __init__(self, db: AsyncSession, app: AppContext) -> None:
        self.db = db
        self.app = app
        self.settings = app.settings

    # --- Consulta ----------------------------------------------------------------------

    async def get(self, asset_id: uuid.UUID, *, for_update: bool = False) -> MediaAsset:
        stmt = select(MediaAsset).where(MediaAsset.id == asset_id)
        if for_update:
            stmt = stmt.with_for_update()
        asset = (await self.db.execute(stmt)).scalar_one_or_none()
        if asset is None:
            raise NotFound("Activo no encontrado")
        return asset

    async def search(
        self,
        *,
        q: str | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        orientation: str | None = None,
        has_audio: bool | None = None,
        consent: str | None = None,
        include_archived: bool = False,
        limit: int = 60,
        offset: int = 0,
    ) -> tuple[list[MediaAsset], int]:
        conditions: list[Any] = []
        if not include_archived:
            conditions.append(MediaAsset.archived_at.is_(None))
        if status:
            conditions.append(MediaAsset.status == status)
        else:
            conditions.append(MediaAsset.status.notin_(["cancelled"]))
        if q:
            like = f"%{q.strip()}%"
            conditions.append(
                or_(
                    MediaAsset.title.ilike(like),
                    MediaAsset.original_filename.ilike(like),
                    MediaAsset.description.ilike(like),
                    MediaAsset.location.ilike(like),
                )
            )
        if tags:
            conditions.append(MediaAsset.tags.contains(normalize_tags(tags)))
        if orientation == "vertical":
            conditions.append(MediaAsset.height > MediaAsset.width * 1.05)
        elif orientation == "horizontal":
            conditions.append(MediaAsset.width > MediaAsset.height * 1.05)
        elif orientation == "square":
            conditions.append(
                and_(
                    MediaAsset.width <= MediaAsset.height * 1.05,
                    MediaAsset.height <= MediaAsset.width * 1.05,
                )
            )
        if has_audio is not None:
            conditions.append(MediaAsset.has_audio.is_(has_audio))
        if consent:
            conditions.append(MediaAsset.consent_status == consent)
        where = and_(*conditions) if conditions else None
        stmt = select(MediaAsset)
        count_stmt = select(func.count()).select_from(MediaAsset)
        if where is not None:
            stmt = stmt.where(where)
            count_stmt = count_stmt.where(where)
        stmt = (
            stmt.order_by(MediaAsset.created_at.desc(), MediaAsset.id).limit(limit).offset(offset)
        )
        items = list((await self.db.execute(stmt)).scalars())
        total = int(await self.db.scalar(count_stmt) or 0)
        return items, total

    async def tag_counts(self) -> list[tuple[str, int]]:
        tag = func.unnest(MediaAsset.tags).label("tag")
        sub = (
            select(tag)
            .where(MediaAsset.archived_at.is_(None), MediaAsset.status == "ready")
            .subquery()
        )
        rows = await self.db.execute(
            select(sub.c.tag, func.count()).group_by(sub.c.tag).order_by(func.count().desc())
        )
        return [(str(t), int(c)) for t, c in rows.all()]

    async def objects(self, asset: MediaAsset) -> dict[str, StoredObject]:
        ids = {
            "original": asset.original_object_id,
            "poster": asset.poster_object_id,
            "strip": asset.strip_object_id,
            "proxy": asset.proxy_object_id,
            "waveform": asset.waveform_object_id,
        }
        wanted = [i for i in ids.values() if i is not None]
        found = {
            o.id: o
            for o in (
                await self.db.execute(select(StoredObject).where(StoredObject.id.in_(wanted)))
            ).scalars()
        }
        return {name: found[i] for name, i in ids.items() if i is not None and i in found}

    def signed_url(self, obj: StoredObject | None, *, filename: str | None = None) -> str | None:
        if obj is None or obj.status != "available":
            return None
        return self.app.storage.presign_get(
            obj.key,
            audience=Audience.BROWSER,
            ttl_seconds=self.settings.download_url_ttl_seconds * 3,
            download_filename=filename,
        ).url

    # --- Subida ------------------------------------------------------------------------

    async def create_upload(
        self,
        ctx: AuditContext,
        *,
        filename: str,
        size_bytes: int,
        content_type: str,
        title: str | None,
    ) -> UploadPlan:
        ext = extension_of(filename)
        if ext not in ALLOWED_EXTENSIONS:
            raise ApiError(
                "Solo se admiten vídeos MP4 o MOV", code="unsupported_format", status_code=422
            )
        if content_type not in ACCEPTED_CONTENT_TYPES:
            raise ApiError(
                f"Tipo de contenido no admitido: {content_type}",
                code="unsupported_format",
                status_code=422,
            )
        if size_bytes <= 0:
            raise ApiError("El fichero está vacío", code="empty_file", status_code=422)
        if size_bytes > self.settings.media_max_upload_bytes:
            raise ApiError(
                "El fichero supera el tamaño máximo permitido",
                code="file_too_large",
                status_code=413,
                details={"max_bytes": self.settings.media_max_upload_bytes},
            )
        part_size = max(self.settings.media_part_size_bytes, math.ceil(size_bytes / 10_000))
        part_count = max(1, math.ceil(size_bytes / part_size))
        real_type = ALLOWED_EXTENSIONS[ext]
        asset_id = uuid.uuid4()
        obj = StoredObject(
            bucket=self.app.storage.bucket,
            key=build_object_key("original", asset_id, extension=ext),
            kind="original",
            status="pending",
            content_type=real_type,
            original_filename=filename[:255],
            created_by_user_id=ctx.actor.id,
        )
        self.db.add(obj)
        await self.db.flush()
        try:
            upload_id = await self.app.storage.create_multipart(obj.key, real_type)
        except Exception as exc:
            raise ApiError(
                "No se pudo iniciar la subida", code="storage_error", status_code=503
            ) from exc
        asset = MediaAsset(
            id=asset_id,
            title=(title or PurePosixPath(filename).stem)[:200] or "Sin título",
            original_filename=filename[:255],
            content_type=real_type,
            declared_size_bytes=size_bytes,
            status="uploading",
            original_object_id=obj.id,
            upload_id=upload_id,
            part_size_bytes=part_size,
            part_count=part_count,
            tags=[],
            people_present="unknown",
            consent_status="pending",
            rights_owner="Grupo Deken",
            created_by_user_id=ctx.actor.id,
        )
        self.db.add(asset)
        await self.db.flush()
        audit.record(
            self.db,
            ctx,
            "media.upload_start",
            target_type="media_asset",
            target_id=asset.id,
            details={"filename": filename[:255], "size_bytes": size_bytes},
        )
        await self.db.commit()
        return UploadPlan(asset=asset, part_size=part_size, part_count=part_count)

    async def part_urls(self, asset_id: uuid.UUID, part_numbers: list[int]) -> list[PartUrl]:
        asset = await self.get(asset_id)
        if asset.status != "uploading" or not asset.upload_id:
            raise Conflict("La subida no está abierta", code="upload_closed")
        if any(n < 1 or n > asset.part_count for n in part_numbers):
            raise ApiError("Número de parte fuera de rango", code="invalid_part", status_code=422)
        if len(part_numbers) > self.settings.media_parts_per_request:
            raise ApiError("Demasiadas partes por petición", code="invalid_part", status_code=422)
        obj = await self.db.get(StoredObject, asset.original_object_id)
        if obj is None:  # pragma: no cover - integridad referencial
            raise NotFound("Objeto original no encontrado")
        return [
            PartUrl(
                part_number=n,
                url=self.app.storage.presign_upload_part(
                    obj.key,
                    asset.upload_id,
                    n,
                    ttl_seconds=self.settings.upload_url_ttl_seconds,
                ).url,
            )
            for n in sorted(set(part_numbers))
        ]

    async def abort_upload(self, ctx: AuditContext, asset_id: uuid.UUID) -> MediaAsset:
        asset = await self.get(asset_id, for_update=True)
        if asset.status != "uploading":
            raise Conflict("La subida ya no está en curso", code="upload_closed")
        obj = await self.db.get(StoredObject, asset.original_object_id)
        if obj is not None and asset.upload_id:
            await self.app.storage.abort_multipart(obj.key, asset.upload_id)
            obj.status = "deleted"
        asset.status = "cancelled"
        asset.upload_id = None
        audit.record(
            self.db, ctx, "media.upload_cancel", target_type="media_asset", target_id=asset.id
        )
        await self.db.commit()
        return asset

    async def _reject(self, asset: MediaAsset, obj: StoredObject, reason: str) -> None:
        """El fichero no es un vídeo válido: se elimina (no es un original aceptado)."""
        asset.status = "rejected"
        asset.status_reason = reason
        obj.status = "rejected"
        try:
            await self.app.storage.delete(obj.key)
            obj.status = "deleted"
        except StorageError as exc:
            log.warning("media.reject_delete_failed", key=obj.key, error=str(exc))

    async def complete_upload(self, ctx: AuditContext, asset_id: uuid.UUID) -> MediaAsset:
        asset = await self.get(asset_id, for_update=True)
        if asset.status != "uploading" or not asset.upload_id:
            raise Conflict("La subida ya se cerró", code="upload_closed")
        obj = await self.db.get(StoredObject, asset.original_object_id)
        if obj is None:  # pragma: no cover
            raise NotFound("Objeto original no encontrado")

        parts = await self.app.storage.list_parts(obj.key, asset.upload_id)
        numbers = sorted(p["PartNumber"] for p in parts)
        uploaded = sum(int(p["Size"]) for p in parts)
        if numbers != list(range(1, asset.part_count + 1)) or uploaded != asset.declared_size_bytes:
            raise ApiError(
                "La subida está incompleta",
                code="upload_incomplete",
                status_code=409,
                details={
                    "parts_expected": asset.part_count,
                    "parts_received": len(numbers),
                    "bytes_expected": asset.declared_size_bytes,
                    "bytes_received": uploaded,
                },
            )
        await self.app.storage.complete_multipart(
            obj.key, asset.upload_id, sorted(parts, key=lambda p: int(p["PartNumber"]))
        )
        asset.upload_id = None
        head = await self.app.storage.head(obj.key)
        if head is None or head.size_bytes != asset.declared_size_bytes:
            await self._reject(asset, obj, "El tamaño almacenado no coincide con el declarado")
            await self.db.commit()
            return asset
        obj.size_bytes = head.size_bytes

        url = self.app.storage.presign_get(obj.key, audience=Audience.INTERNAL, ttl_seconds=600).url
        try:
            summary = await probe_url(
                self.settings.ffprobe_path, url, timeout_s=self.settings.ffprobe_timeout_seconds
            )
            problem = self._media_problem(summary)
        except ProbeError as exc:
            summary, problem = None, f"No es un vídeo legible: {exc}"
        if problem or summary is None:
            await self._reject(asset, obj, problem or "No es un vídeo válido")
            audit.record(
                self.db,
                ctx,
                "media.upload_rejected",
                outcome="failure",
                target_type="media_asset",
                target_id=asset.id,
                details={"reason": asset.status_reason},
            )
            await self.db.commit()
            return asset

        self._apply_probe(asset, summary)
        obj.status = "available"
        obj.media_info = summary.model_dump(mode="json")
        obj.verified_at = _now()
        asset.status = "processing"
        asset.status_reason = None
        job = await self._create_ingest_job(ctx, asset, obj)
        asset.ingest_job_id = job.id
        audit.record(
            self.db, ctx, "media.upload_complete", target_type="media_asset", target_id=asset.id
        )
        await self.db.commit()
        await JobService(self.db, self.app).wake(job.queue)
        return asset

    @staticmethod
    def _media_problem(summary: ProbeSummary) -> str | None:
        containers = set(summary.format_name.split(","))
        if not containers & VIDEO_CONTAINERS:
            return f"Contenedor '{summary.format_name}' no es MP4/MOV"
        videos = [v for v in summary.video_streams if v.codec_name not in {"mjpeg", "png"}]
        if not videos:
            return "El fichero no contiene ninguna pista de vídeo"
        if not videos[0].width or not videos[0].height:
            return "La pista de vídeo no tiene dimensiones"
        if not summary.duration_s or summary.duration_s <= 0:
            return "El vídeo no tiene duración"
        return None

    @staticmethod
    def _apply_probe(asset: MediaAsset, summary: ProbeSummary) -> None:
        video = next(v for v in summary.video_streams if v.codec_name not in {"mjpeg", "png"})
        display = video.display_size or (video.width or 0, video.height or 0)
        audio = summary.audio_streams[0] if summary.audio_streams else None
        asset.container = summary.format_name[:100]
        asset.duration_s = summary.duration_s
        asset.width, asset.height = display
        asset.rotation = video.rotation or 0
        asset.fps = video.avg_frame_rate or video.r_frame_rate
        asset.video_codec = video.codec_name
        asset.audio_codec = audio.codec_name if audio else None
        asset.has_audio = audio is not None
        asset.bit_rate = summary.bit_rate
        asset.probe = summary.model_dump(mode="json")

    async def _create_ingest_job(
        self, ctx: AuditContext, asset: MediaAsset, obj: StoredObject
    ) -> Job:
        width, height = proxy_size(asset.width or 16, asset.height or 16)
        payload = MediaIngestPayload(
            asset_id=asset.id,
            inputs=[
                InputRef(
                    name="original",
                    object_id=obj.id,
                    kind="video",
                    extension=extension_of(asset.original_filename) or "mp4",
                    width=asset.width,
                    height=asset.height,
                    duration_s=asset.duration_s,
                    has_audio=asset.has_audio,
                )
            ],
            proxy=ProxyTarget(
                width=width,
                height=height,
                fps=snap_fps(asset.fps),
                duration_s=asset.duration_s or 1.0,
                has_audio=bool(asset.has_audio),
            ),
        )
        return await JobService(self.db, self.app).create(
            JobType.MEDIA_INGEST.value, payload.model_dump(mode="json"), ctx=ctx, commit=False
        )

    # --- Resultado de la ingesta ---------------------------------------------------------

    async def ingest_finished(self, job: Job) -> None:
        """Hook de fin de `media.ingest` (en la transacción del trabajo)."""
        asset_id = uuid.UUID(str(job.payload["asset_id"]))
        asset = await self.get(asset_id, for_update=True)
        if asset.ingest_job_id != job.id:
            return
        if job.status == JobStatus.COMPLETED.value:
            await self._apply_ingest(asset, job)
        elif job.status == JobStatus.FAILED.value:
            error = job.error or {}
            invalid = error.get("code") == "invalid_media"
            asset.status = "rejected" if invalid else "failed"
            asset.status_reason = str(error.get("message") or "Error en la ingesta")
        elif job.status == JobStatus.CANCELLED.value:
            asset.status = "failed"
            asset.status_reason = "Ingesta cancelada"

    async def ingest_requeued(self, job: Job) -> None:
        asset = await self.get(uuid.UUID(str(job.payload["asset_id"])), for_update=True)
        if asset.ingest_job_id == job.id and asset.status in {"failed", "rejected"}:
            asset.status = "processing"
            asset.status_reason = None

    async def _apply_ingest(self, asset: MediaAsset, job: Job) -> None:
        result = job.result or {}
        # La sesión no hace autoflush: las salidas recién verificadas siguen pendientes.
        await self.db.flush()
        outputs = {
            o.name: o
            for o in (
                await self.db.execute(
                    select(JobOutput).where(
                        JobOutput.job_id == job.id,
                        JobOutput.attempt == job.attempts,
                        JobOutput.verified.is_(True),
                    )
                )
            ).scalars()
        }
        asset.poster_object_id = outputs["poster"].object_id if "poster" in outputs else None
        asset.strip_object_id = outputs["strip"].object_id if "strip" in outputs else None
        asset.proxy_object_id = outputs["proxy"].object_id if "proxy" in outputs else None
        asset.waveform_object_id = outputs["waveform"].object_id if "waveform" in outputs else None
        asset.strip_frames = int(result.get("strip_frames") or 0) or None
        sha = str(result.get("sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            asset.status = "failed"
            asset.status_reason = "La ingesta no devolvió un SHA-256 válido"
            return
        asset.sha256 = sha
        original = await self.db.get(StoredObject, asset.original_object_id)
        if original is not None:
            original.sha256 = sha
        duplicate = (
            await self.db.execute(
                select(MediaAsset)
                .where(
                    MediaAsset.sha256 == sha,
                    MediaAsset.id != asset.id,
                    MediaAsset.status == "ready",
                    MediaAsset.archived_at.is_(None),
                )
                .order_by(MediaAsset.created_at)
                .limit(1)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            asset.status = "duplicate"
            asset.duplicate_of_id = duplicate.id
            asset.status_reason = f"Mismo contenido que «{duplicate.title}»"
            return
        asset.status = "ready"
        asset.status_reason = None

    # --- Catalogación y derechos -------------------------------------------------------------

    async def update_metadata(
        self, ctx: AuditContext, asset_id: uuid.UUID, changes: dict[str, Any]
    ) -> MediaAsset:
        asset = await self.get(asset_id, for_update=True)
        if "tags" in changes and changes["tags"] is not None:
            changes["tags"] = normalize_tags(changes["tags"])
        applied: dict[str, Any] = {}
        for field in ("title", "description", "tags", "recorded_at", "location"):
            if (
                field in changes
                and changes[field] is not None
                and getattr(asset, field) != changes[field]
            ):
                setattr(asset, field, changes[field])
                applied[field] = changes[field] if field != "recorded_at" else str(changes[field])
        if applied:
            audit.record(
                self.db,
                ctx,
                "media.update",
                target_type="media_asset",
                target_id=asset.id,
                details=applied,
            )
        await self.db.commit()
        return asset

    async def update_rights(
        self, ctx: AuditContext, asset_id: uuid.UUID, changes: dict[str, Any]
    ) -> MediaAsset:
        asset = await self.get(asset_id, for_update=True)
        before = {
            f: getattr(asset, f)
            for f in (
                "people_present",
                "consent_status",
                "consent_reference",
                "usage_restrictions",
                "rights_owner",
            )
        }
        for field, value in changes.items():
            if value is not None and field in before:
                setattr(asset, field, value)
        if asset.people_present == "no" and asset.consent_status == "pending":
            asset.consent_status = "not_required"
        if asset.consent_status == "granted" and not asset.consent_reference:
            raise ApiError(
                "Indica la referencia del documento de consentimiento",
                code="consent_reference_required",
                status_code=422,
            )
        after = {f: getattr(asset, f) for f in before}
        diff = {f: {"from": before[f], "to": after[f]} for f in before if before[f] != after[f]}
        if diff:
            asset.rights_updated_by_user_id = ctx.actor.id
            asset.rights_updated_at = _now()
            audit.record(
                self.db,
                ctx,
                "media.rights_update",
                target_type="media_asset",
                target_id=asset.id,
                details=diff,
            )
        await self.db.commit()
        return asset

    async def archive(self, ctx: AuditContext, asset_id: uuid.UUID) -> MediaAsset:
        """Archiva el activo (deja de aparecer). El original se conserva intacto."""
        asset = await self.get(asset_id, for_update=True)
        if asset.archived_at is None:
            asset.archived_at = _now()
            audit.record(
                self.db, ctx, "media.archive", target_type="media_asset", target_id=asset.id
            )
        await self.db.commit()
        return asset

    async def original_download(
        self, ctx: AuditContext, asset_id: uuid.UUID
    ) -> tuple[MediaAsset, str]:
        asset = await self.get(asset_id)
        obj = await self.db.get(StoredObject, asset.original_object_id)
        if obj is None or obj.status != "available":
            raise Conflict("El original no está disponible", code="not_available")
        url = self.app.storage.presign_get(
            obj.key,
            audience=Audience.BROWSER,
            ttl_seconds=self.settings.download_url_ttl_seconds,
            download_filename=asset.original_filename,
        ).url
        audit.record(
            self.db, ctx, "media.original_download", target_type="media_asset", target_id=asset.id
        )
        await self.db.commit()
        return asset, url
