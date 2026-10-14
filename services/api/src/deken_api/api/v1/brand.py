"""Marca DEKEN: logos, tipografías e imágenes corporativas oficiales."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, status

from deken_api.api.v1.schemas import (
    BrandAssetOut,
    BrandUpdateRequest,
    BrandUploadOut,
    BrandUploadRequest,
    DownloadUrlOut,
)
from deken_api.db.models import BrandAsset, StoredObject
from deken_api.deps import Ctx, Db, Principal, require
from deken_api.errors import Conflict
from deken_api.integrations.storage import Audience
from deken_api.security.rbac import Permission
from deken_api.services.brand import BrandService

router = APIRouter(prefix="/brand", tags=["brand"])

Reader = require(Permission.BRAND_READ)
Manager = require(Permission.BRAND_MANAGE)


async def brand_out(service: BrandService, asset: BrandAsset) -> BrandAssetOut:
    preview = (
        await service.db.get(StoredObject, asset.preview_object_id)
        if asset.preview_object_id
        else None
    )
    return BrandAssetOut(
        id=asset.id,
        kind=asset.kind,  # type: ignore[arg-type]
        name=asset.name,
        family=asset.family,
        status=asset.status,
        status_reason=asset.status_reason,
        original_filename=asset.original_filename,
        width=asset.width,
        height=asset.height,
        aspect_ratio=asset.aspect_ratio,
        has_alpha=asset.has_alpha,
        declared_color=asset.declared_color,
        measured_color_name=asset.measured_color_name,
        measured_color_hex=asset.measured_color_hex,
        color_mismatch=asset.color_mismatch,
        recommended_background=asset.recommended_background,  # type: ignore[arg-type]
        usage_background=asset.usage_background,  # type: ignore[arg-type]
        font_family=asset.font_family,
        font_style=asset.font_style,
        font_weight=asset.font_weight,
        license_ref=asset.license_ref,
        notes=asset.notes,
        analysis=asset.analysis,
        preview_url=service.preview_url(preview),
        created_at=asset.created_at,
    )


@router.post("/uploads", response_model=BrandUploadOut, status_code=status.HTTP_201_CREATED)
async def start_brand_upload(
    body: BrandUploadRequest, db: Db, ctx: Ctx, principal: Principal = Manager
) -> BrandUploadOut:
    upload = await BrandService(db, ctx).create_upload(
        principal.audit,
        kind=body.kind,
        name=body.name,
        filename=body.filename,
        size_bytes=body.size_bytes,
        declared_color=body.declared_color,
        family=body.family,
        license_ref=body.license_ref,
    )
    return BrandUploadOut(
        asset_id=upload.asset.id, upload_url=upload.upload_url, headers=upload.headers
    )


@router.post("/uploads/{asset_id}/complete", response_model=BrandAssetOut)
async def complete_brand_upload(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = Manager
) -> BrandAssetOut:
    service = BrandService(db, ctx)
    return await brand_out(service, await service.complete_upload(principal.audit, asset_id))


@router.get("/assets", response_model=list[BrandAssetOut])
async def list_brand_assets(
    db: Db, ctx: Ctx, kind: str | None = None, _: Principal = Reader
) -> list[BrandAssetOut]:
    service = BrandService(db, ctx)
    return [await brand_out(service, a) for a in await service.list(kind=kind)]


@router.get("/assets/{asset_id}", response_model=BrandAssetOut)
async def get_brand_asset(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, _: Principal = Reader
) -> BrandAssetOut:
    service = BrandService(db, ctx)
    return await brand_out(service, await service.get(asset_id))


@router.patch("/assets/{asset_id}", response_model=BrandAssetOut)
async def update_brand_asset(
    asset_id: uuid.UUID, body: BrandUpdateRequest, db: Db, ctx: Ctx, principal: Principal = Manager
) -> BrandAssetOut:
    service = BrandService(db, ctx)
    return await brand_out(
        service,
        await service.update(principal.audit, asset_id, body.model_dump(exclude_unset=True)),
    )


@router.post("/assets/{asset_id}/archive", response_model=BrandAssetOut)
async def archive_brand_asset(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = Manager
) -> BrandAssetOut:
    service = BrandService(db, ctx)
    return await brand_out(service, await service.archive(principal.audit, asset_id))


@router.get("/assets/{asset_id}/download-url", response_model=DownloadUrlOut)
async def brand_download_url(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, _: Principal = Reader
) -> DownloadUrlOut:
    service = BrandService(db, ctx)
    asset = await service.get(asset_id)
    obj = await db.get(StoredObject, asset.object_id)
    if obj is None or obj.status != "available":
        raise Conflict("El fichero no está disponible", code="not_available")
    ttl = ctx.settings.download_url_ttl_seconds
    url = ctx.storage.presign_get(
        obj.key,
        audience=Audience.BROWSER,
        ttl_seconds=ttl,
        download_filename=asset.original_filename,
    ).url
    return DownloadUrlOut(
        url=url,
        expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
        filename=asset.original_filename,
    )
