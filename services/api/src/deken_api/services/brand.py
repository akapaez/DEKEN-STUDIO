"""Recursos oficiales de marca: logos, tipografías e imágenes corporativas.

Al subir un logo la API lo analiza de verdad (no se fía del nombre del fichero, que en
el kit de DEKEN tiene al menos dos casos intercambiados): proporción, transparencia,
color dominante medido y fondo recomendado según el contraste con los neutros de marca.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

import anyio
from fontTools.ttLib import TTFont, TTLibError
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.context import AppContext
from deken_api.db.models import BrandAsset, StoredObject
from deken_api.errors import ApiError, Conflict, NotFound
from deken_api.integrations.storage import Audience, StorageError, build_object_key
from deken_api.services import audit
from deken_api.services.audit import AuditContext

# Colores medidos sobre los logos reales (guía de marca DEKEN).
REFERENCE_INKS: dict[str, tuple[int, int, int]] = {
    "verde": (0x76, 0xB8, 0x2A),
    "gris": (0x38, 0x3E, 0x42),
    "blanco": (0xFF, 0xFF, 0xFF),
    "negro": (0x0D, 0x0E, 0x0F),
}
# Proporciones de las familias de logo (ancho / alto).
FAMILY_RATIOS = {
    "DEKEN": 5.2,
    "GD": 1.3,
    "GRUPO-DEKEN": 2.15,
    "GRUPO-DEKEN-HORIZONTAL": 11.0,
}
IMAGE_TYPES = {"png": "image/png", "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
FONT_TYPES = {"ttf": "font/ttf", "otf": "font/otf"}
SECONDARY_INK_MIN_SHARE = 0.15
MAX_PIXELS = 60_000_000  # protección frente a "bombas de descompresión"

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def _now() -> datetime:
    return datetime.now(UTC)


def _ext(filename: str) -> str:
    return PurePosixPath(filename.replace("\\", "/")).suffix.lower().lstrip(".")


def declared_color_from_name(filename: str) -> str | None:
    """`GRUPO-DEKEN-HORIZONTAL-BLANCO.png` → `blanco`; `DEKEN-VERDE-GRIS.png` → `verde-gris`."""
    stem = PurePosixPath(filename).stem.lower()
    found = [
        ink
        for ink in ("verde", "gris", "blanco", "negro")
        if re.search(rf"(^|[-_ ]){ink}($|[-_ ])", stem)
    ]
    if not found:
        return None
    order = sorted(found, key=lambda ink: stem.index(ink))
    return "-".join(order[:2])


def family_from_ratio(ratio: float) -> str | None:
    best = min(FAMILY_RATIOS.items(), key=lambda kv: abs(ratio - kv[1]) / kv[1])
    return best[0] if abs(ratio - best[1]) / best[1] <= 0.12 else None


def _nearest_ink(rgb: tuple[int, int, int]) -> str:
    return min(
        REFERENCE_INKS,
        key=lambda name: sum((a - b) ** 2 for a, b in zip(rgb, REFERENCE_INKS[name], strict=True)),
    )


@dataclass(frozen=True)
class LogoAnalysis:
    width: int
    height: int
    aspect_ratio: float
    has_alpha: bool
    measured_name: str
    measured_hex: str
    shares: dict[str, float]
    recommended_background: str
    family_guess: str | None


def analyze_logo(data: bytes) -> tuple[LogoAnalysis, bytes]:
    """Analiza un logo y devuelve también una vista previa PNG (lado mayor ≤ 512 px)."""
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ApiError(
            f"La imagen no es válida: {exc}", code="invalid_image", status_code=422
        ) from exc
    if image.format not in {"PNG", "WEBP", "JPEG"}:
        raise ApiError("Formato de imagen no admitido", code="invalid_image", status_code=422)
    width, height = image.size
    has_alpha = image.mode in {"RGBA", "LA", "PA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    rgba = image.convert("RGBA")
    sample = rgba.copy()
    sample.thumbnail((256, 256), Image.Resampling.NEAREST)
    raw = sample.tobytes()  # RGBA, 4 bytes por píxel
    pixels = [
        (raw[i], raw[i + 1], raw[i + 2], raw[i + 3])
        for i in range(0, len(raw), 4)
        if raw[i + 3] >= 200
    ]
    if not pixels:
        raise ApiError(
            "El logo es completamente transparente", code="invalid_image", status_code=422
        )
    counts: Counter[str] = Counter()
    sums: dict[str, list[int]] = {}
    for r, g, b, _ in pixels:
        ink = _nearest_ink((r, g, b))
        counts[ink] += 1
        acc = sums.setdefault(ink, [0, 0, 0])
        acc[0] += r
        acc[1] += g
        acc[2] += b
    total = sum(counts.values())
    shares = {ink: round(n / total, 3) for ink, n in counts.most_common()}
    ranked = [ink for ink, _ in counts.most_common()]
    main = ranked[0]
    secondary = (
        ranked[1] if len(ranked) > 1 and shares[ranked[1]] >= SECONDARY_INK_MIN_SHARE else None
    )
    measured_name = f"{main}-{secondary}" if secondary else main
    n = counts[main]
    measured_hex = "#{:02X}{:02X}{:02X}".format(*(v // n for v in sums[main]))
    inks = {main, secondary} - {None}
    # Fondo recomendado por contraste: claro sobre oscuro y viceversa. El verde va sobre
    # oscuro (7,97:1); sobre blanco solo da 2,42:1.
    if inks <= {"blanco", "verde"}:
        recommended = "dark"
    elif inks <= {"gris", "negro"} or inks == {"verde", "gris"} or inks == {"verde", "negro"}:
        recommended = "light"
    else:
        recommended = "any"
    preview = rgba.copy()
    preview.thumbnail((512, 512), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    preview.save(buf, format="PNG", optimize=True)
    ratio = round(width / height, 3)
    return (
        LogoAnalysis(
            width=width,
            height=height,
            aspect_ratio=ratio,
            has_alpha=has_alpha,
            measured_name=measured_name,
            measured_hex=measured_hex,
            shares=shares,
            recommended_background=recommended,
            family_guess=family_from_ratio(ratio),
        ),
        buf.getvalue(),
    )


@dataclass(frozen=True)
class FontAnalysis:
    family: str
    style: str
    weight: int
    italic: bool
    glyphs: int


def analyze_font(data: bytes) -> FontAnalysis:
    try:
        font = TTFont(io.BytesIO(data), lazy=True)
        names = font["name"]
        family = str(names.getDebugName(16) or names.getDebugName(1) or "").strip()
        style = str(names.getDebugName(17) or names.getDebugName(2) or "").strip()
        os2 = font["OS/2"]
        weight = int(os2.usWeightClass)
        italic = bool(os2.fsSelection & 0b1) or "italic" in style.lower()
        glyphs = len(font.getGlyphOrder())
    except (TTLibError, KeyError, AttributeError, ValueError) as exc:
        raise ApiError(
            f"La tipografía no es válida: {exc}", code="invalid_font", status_code=422
        ) from exc
    if not family:
        raise ApiError("La tipografía no declara su familia", code="invalid_font", status_code=422)
    return FontAnalysis(
        family=family[:100],
        style=style[:50] or "Regular",
        weight=weight,
        italic=italic,
        glyphs=glyphs,
    )


@dataclass(frozen=True)
class BrandUpload:
    asset: BrandAsset
    upload_url: str
    headers: dict[str, str]


class BrandService:
    def __init__(self, db: AsyncSession, app: AppContext) -> None:
        self.db = db
        self.app = app
        self.settings = app.settings

    async def get(self, asset_id: uuid.UUID, *, for_update: bool = False) -> BrandAsset:
        stmt = select(BrandAsset).where(BrandAsset.id == asset_id)
        if for_update:
            stmt = stmt.with_for_update()
        asset = (await self.db.execute(stmt)).scalar_one_or_none()
        if asset is None:
            raise NotFound("Recurso de marca no encontrado")
        return asset

    async def list(self, *, kind: str | None = None) -> list[BrandAsset]:
        stmt = select(BrandAsset).where(
            BrandAsset.archived_at.is_(None), BrandAsset.status == "ready"
        )
        if kind:
            stmt = stmt.where(BrandAsset.kind == kind)
        return list(
            (await self.db.execute(stmt.order_by(BrandAsset.kind, BrandAsset.name))).scalars()
        )

    async def create_upload(
        self,
        ctx: AuditContext,
        *,
        kind: str,
        name: str,
        filename: str,
        size_bytes: int,
        declared_color: str | None,
        family: str | None,
        license_ref: str | None,
    ) -> BrandUpload:
        ext = _ext(filename)
        allowed = FONT_TYPES if kind == "font" else IMAGE_TYPES
        if kind == "logo" and ext not in {"png", "webp"}:
            raise ApiError(
                "Los logos deben ser PNG o WebP con transparencia",
                code="unsupported_format",
                status_code=422,
            )
        if ext not in allowed:
            raise ApiError(
                "Formato no admitido para este recurso", code="unsupported_format", status_code=422
            )
        if not 0 < size_bytes <= self.settings.brand_max_upload_bytes:
            raise ApiError("Tamaño de fichero no permitido", code="file_too_large", status_code=413)
        content_type = allowed[ext]
        asset_id = uuid.uuid4()
        obj = StoredObject(
            bucket=self.app.storage.bucket,
            key=build_object_key("brand", asset_id, extension=ext),
            kind="brand",
            status="pending",
            content_type=content_type,
            original_filename=filename[:255],
            created_by_user_id=ctx.actor.id,
        )
        self.db.add(obj)
        await self.db.flush()
        asset = BrandAsset(
            id=asset_id,
            kind=kind,
            name=name.strip()[:200],
            family=family,
            declared_color=declared_color
            or (declared_color_from_name(filename) if kind == "logo" else None),
            status="uploading",
            object_id=obj.id,
            original_filename=filename[:255],
            content_type=content_type,
            declared_size_bytes=size_bytes,
            color_mismatch=False,
            license_ref=license_ref,
            created_by_user_id=ctx.actor.id,
        )
        self.db.add(asset)
        audit.record(
            self.db,
            ctx,
            "brand.upload_start",
            target_type="brand_asset",
            target_id=asset_id,
            details={"kind": kind, "filename": filename[:255]},
        )
        await self.db.commit()
        signed = self.app.storage.presign_put(
            obj.key,
            audience=Audience.BROWSER,
            ttl_seconds=self.settings.upload_url_ttl_seconds,
            content_type=content_type,
        )
        return BrandUpload(asset=asset, upload_url=signed.url, headers=signed.headers)

    async def complete_upload(self, ctx: AuditContext, asset_id: uuid.UUID) -> BrandAsset:
        asset = await self.get(asset_id, for_update=True)
        if asset.status != "uploading":
            raise Conflict("La subida ya se cerró", code="upload_closed")
        obj = await self.db.get(StoredObject, asset.object_id)
        if obj is None:  # pragma: no cover
            raise NotFound("Objeto no encontrado")
        head = await self.app.storage.head(obj.key)
        if head is None or head.size_bytes != asset.declared_size_bytes:
            raise ApiError("La subida está incompleta", code="upload_incomplete", status_code=409)
        data = await self.app.storage.get_bytes(
            obj.key, max_bytes=self.settings.brand_max_upload_bytes
        )
        asset.sha256 = hashlib.sha256(data).hexdigest()
        obj.sha256 = asset.sha256
        obj.size_bytes = len(data)
        try:
            if asset.kind == "font":
                await self._apply_font(asset, data)
            else:
                await self._apply_image(asset, obj, data)
        except ApiError as exc:
            asset.status = "rejected"
            asset.status_reason = exc.message
            obj.status = "rejected"
            with contextlib.suppress(StorageError):
                await self.app.storage.delete(obj.key)
                obj.status = "deleted"
            audit.record(
                self.db,
                ctx,
                "brand.upload_rejected",
                outcome="failure",
                target_type="brand_asset",
                target_id=asset.id,
                details={"reason": exc.message},
            )
            await self.db.commit()
            return asset
        obj.status = "available"
        obj.verified_at = _now()
        asset.status = "ready"
        audit.record(
            self.db, ctx, "brand.upload_complete", target_type="brand_asset", target_id=asset.id
        )
        await self.db.commit()
        return asset

    async def _apply_font(self, asset: BrandAsset, data: bytes) -> None:
        info = await anyio.to_thread.run_sync(analyze_font, data)
        asset.font_family = info.family
        asset.font_style = info.style
        asset.font_weight = info.weight
        asset.analysis = {"italic": info.italic, "glyphs": info.glyphs}
        if info.italic:
            asset.notes = "La guía de marca prohíbe la cursiva: no usar en piezas."

    async def _apply_image(self, asset: BrandAsset, obj: StoredObject, data: bytes) -> None:
        info, preview = await anyio.to_thread.run_sync(analyze_logo, data)
        asset.width, asset.height = info.width, info.height
        asset.aspect_ratio = info.aspect_ratio
        asset.has_alpha = info.has_alpha
        asset.measured_color_name = info.measured_name
        asset.measured_color_hex = info.measured_hex
        asset.recommended_background = info.recommended_background
        asset.family = asset.family or info.family_guess
        asset.color_mismatch = bool(
            asset.kind == "logo"
            and asset.declared_color
            and asset.declared_color.split("-")[0] != info.measured_name.split("-")[0]
        )
        asset.analysis = {
            "ink_shares": info.shares,
            "family_guess": info.family_guess,
            "warnings": [
                w
                for w in (
                    None
                    if info.has_alpha or asset.kind != "logo"
                    else "El logo no tiene transparencia",
                    "El color medido no coincide con el declarado en el nombre"
                    if asset.color_mismatch
                    else None,
                )
                if w
            ],
        }
        preview_obj = StoredObject(
            bucket=self.app.storage.bucket,
            key=build_object_key("brand", asset.id, extension="png"),
            kind="brand",
            status="available",
            content_type="image/png",
            size_bytes=len(preview),
            verified_at=_now(),
            created_by_user_id=obj.created_by_user_id,
        )
        await self.app.storage.put_bytes(preview_obj.key, preview, "image/png")
        self.db.add(preview_obj)
        await self.db.flush()
        asset.preview_object_id = preview_obj.id

    async def update(
        self, ctx: AuditContext, asset_id: uuid.UUID, changes: dict[str, Any]
    ) -> BrandAsset:
        asset = await self.get(asset_id, for_update=True)
        applied: dict[str, Any] = {}
        for field in (
            "name",
            "usage_background",
            "family",
            "declared_color",
            "notes",
            "license_ref",
        ):
            if (
                field in changes
                and changes[field] is not None
                and getattr(asset, field) != changes[field]
            ):
                setattr(asset, field, changes[field])
                applied[field] = changes[field]
        if "declared_color" in applied and asset.measured_color_name and asset.declared_color:
            asset.color_mismatch = (
                asset.declared_color.split("-")[0] != asset.measured_color_name.split("-")[0]
            )
        if applied:
            audit.record(
                self.db,
                ctx,
                "brand.update",
                target_type="brand_asset",
                target_id=asset.id,
                details=applied,
            )
        await self.db.commit()
        return asset

    async def archive(self, ctx: AuditContext, asset_id: uuid.UUID) -> BrandAsset:
        asset = await self.get(asset_id, for_update=True)
        if asset.archived_at is None:
            asset.archived_at = _now()
            audit.record(
                self.db, ctx, "brand.archive", target_type="brand_asset", target_id=asset.id
            )
        await self.db.commit()
        return asset

    def preview_url(self, obj: StoredObject | None) -> str | None:
        if obj is None or obj.status != "available":
            return None
        return self.app.storage.presign_get(
            obj.key,
            audience=Audience.BROWSER,
            ttl_seconds=self.settings.download_url_ttl_seconds * 3,
        ).url
