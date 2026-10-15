"""Biblioteca audiovisual: subidas multiparte, catálogo, derechos y reproducción."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Query, status

from deken_api.api.v1.schemas import (
    DownloadUrlOut,
    MediaAssetDetailOut,
    MediaAssetOut,
    MediaListOut,
    MediaRightsRequest,
    MediaUpdateRequest,
    MediaUploadOut,
    MediaUploadRequest,
    PartUrlOut,
    PartUrlsRequest,
    StoredObjectOut,
    TagCountOut,
    WaveformOut,
)
from deken_api.db.models import MediaAsset, StoredObject
from deken_api.deps import Ctx, Db, Principal, require
from deken_api.errors import NotFound
from deken_api.security.rbac import Permission
from deken_api.services.media import (
    MediaService,
    dynamic_range_of,
    orientation_of,
    usable_for_production,
)

router = APIRouter(prefix="/media", tags=["media"])

Reader = require(Permission.MEDIA_READ)
Writer = require(Permission.MEDIA_WRITE)


def asset_out(
    service: MediaService, asset: MediaAsset, objects: dict[str, StoredObject]
) -> MediaAssetOut:
    return MediaAssetOut(
        id=asset.id,
        title=asset.title,
        description=asset.description,
        original_filename=asset.original_filename,
        status=asset.status,  # type: ignore[arg-type]
        status_reason=asset.status_reason,
        declared_size_bytes=asset.declared_size_bytes,
        sha256=asset.sha256,
        duplicate_of_id=asset.duplicate_of_id,
        container=asset.container,
        duration_s=asset.duration_s,
        width=asset.width,
        height=asset.height,
        orientation=orientation_of(asset.width, asset.height),
        dynamic_range=dynamic_range_of(asset),  # type: ignore[arg-type]
        rotation=asset.rotation,
        fps=asset.fps,
        video_codec=asset.video_codec,
        audio_codec=asset.audio_codec,
        has_audio=asset.has_audio,
        tags=list(asset.tags or []),
        recorded_at=asset.recorded_at,
        location=asset.location,
        people_present=asset.people_present,  # type: ignore[arg-type]
        consent_status=asset.consent_status,  # type: ignore[arg-type]
        consent_reference=asset.consent_reference,
        usage_restrictions=asset.usage_restrictions,
        rights_owner=asset.rights_owner,
        rights_updated_at=asset.rights_updated_at,
        usable_for_production=usable_for_production(asset),
        ingest_job_id=asset.ingest_job_id,
        poster_url=service.signed_url(objects.get("poster")),
        strip_url=service.signed_url(objects.get("strip")),
        strip_frames=asset.strip_frames,
        created_at=asset.created_at,
        archived_at=asset.archived_at,
    )


async def detail_out(service: MediaService, asset: MediaAsset) -> MediaAssetDetailOut:
    objects = await service.objects(asset)
    base = asset_out(service, asset, objects)
    original = objects.get("original")
    return MediaAssetDetailOut(
        **base.model_dump(),
        proxy_url=service.signed_url(objects.get("proxy")),
        has_waveform="waveform" in objects and objects["waveform"].status == "available",
        original_object=StoredObjectOut.model_validate(original) if original else None,
        derivatives={
            name: StoredObjectOut.model_validate(obj)
            for name, obj in objects.items()
            if name != "original"
        },
        probe=asset.probe,
    )


@router.post("/uploads", response_model=MediaUploadOut, status_code=status.HTTP_201_CREATED)
async def start_media_upload(
    body: MediaUploadRequest, db: Db, ctx: Ctx, principal: Principal = Writer
) -> MediaUploadOut:
    plan = await MediaService(db, ctx).create_upload(
        principal.audit,
        filename=body.filename,
        size_bytes=body.size_bytes,
        content_type=body.content_type,
        title=body.title,
    )
    return MediaUploadOut(
        asset_id=plan.asset.id,
        part_size_bytes=plan.part_size,
        part_count=plan.part_count,
        max_parts_per_request=ctx.settings.media_parts_per_request,
    )


@router.post("/uploads/{asset_id}/parts", response_model=list[PartUrlOut])
async def media_upload_parts(
    asset_id: uuid.UUID, body: PartUrlsRequest, db: Db, ctx: Ctx, _: Principal = Writer
) -> list[PartUrlOut]:
    urls = await MediaService(db, ctx).part_urls(asset_id, body.part_numbers)
    return [PartUrlOut(part_number=u.part_number, url=u.url) for u in urls]


@router.post("/uploads/{asset_id}/complete", response_model=MediaAssetDetailOut)
async def complete_media_upload(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = Writer
) -> MediaAssetDetailOut:
    service = MediaService(db, ctx)
    asset = await service.complete_upload(principal.audit, asset_id)
    return await detail_out(service, asset)


@router.post("/uploads/{asset_id}/abort", response_model=MediaAssetOut)
async def abort_media_upload(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = Writer
) -> MediaAssetOut:
    service = MediaService(db, ctx)
    asset = await service.abort_upload(principal.audit, asset_id)
    return asset_out(service, asset, {})


@router.get("/assets", response_model=MediaListOut)
async def list_media_assets(
    db: Db,
    ctx: Ctx,
    q: str | None = Query(default=None, max_length=200),
    tag: list[str] = Query(default_factory=list),
    status_filter: str | None = Query(default=None, alias="status", max_length=16),
    orientation: Literal["vertical", "horizontal", "square"] | None = None,
    has_audio: bool | None = None,
    consent: Literal["not_required", "pending", "granted", "denied"] | None = None,
    include_archived: bool = False,
    limit: int = Query(default=60, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: Principal = Reader,
) -> MediaListOut:
    service = MediaService(db, ctx)
    items, total = await service.search(
        q=q,
        tags=tag,
        status=status_filter,
        orientation=orientation,
        has_audio=has_audio,
        consent=consent,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    out = []
    for asset in items:
        out.append(asset_out(service, asset, await service.objects(asset)))
    return MediaListOut(items=out, total=total)


@router.get("/tags", response_model=list[TagCountOut])
async def list_media_tags(db: Db, ctx: Ctx, _: Principal = Reader) -> list[TagCountOut]:
    return [TagCountOut(tag=t, count=c) for t, c in await MediaService(db, ctx).tag_counts()]


@router.get("/assets/{asset_id}", response_model=MediaAssetDetailOut)
async def get_media_asset(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, _: Principal = Reader
) -> MediaAssetDetailOut:
    service = MediaService(db, ctx)
    return await detail_out(service, await service.get(asset_id))


@router.patch("/assets/{asset_id}", response_model=MediaAssetDetailOut)
async def update_media_asset(
    asset_id: uuid.UUID, body: MediaUpdateRequest, db: Db, ctx: Ctx, principal: Principal = Writer
) -> MediaAssetDetailOut:
    service = MediaService(db, ctx)
    asset = await service.update_metadata(
        principal.audit, asset_id, body.model_dump(exclude_unset=True)
    )
    return await detail_out(service, asset)


@router.put("/assets/{asset_id}/rights", response_model=MediaAssetDetailOut)
async def update_media_rights(
    asset_id: uuid.UUID,
    body: MediaRightsRequest,
    db: Db,
    ctx: Ctx,
    principal: Principal = require(Permission.MEDIA_RIGHTS),
) -> MediaAssetDetailOut:
    service = MediaService(db, ctx)
    asset = await service.update_rights(
        principal.audit, asset_id, body.model_dump(exclude_unset=True)
    )
    return await detail_out(service, asset)


@router.post("/assets/{asset_id}/archive", response_model=MediaAssetDetailOut)
async def archive_media_asset(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = Writer
) -> MediaAssetDetailOut:
    service = MediaService(db, ctx)
    return await detail_out(service, await service.archive(principal.audit, asset_id))


@router.get("/assets/{asset_id}/original-url", response_model=DownloadUrlOut)
async def media_original_url(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = Reader
) -> DownloadUrlOut:
    service = MediaService(db, ctx)
    asset, url = await service.original_download(principal.audit, asset_id)
    return DownloadUrlOut(
        url=url,
        expires_at=datetime.now(UTC) + timedelta(seconds=ctx.settings.download_url_ttl_seconds),
        filename=asset.original_filename,
    )


@router.get("/assets/{asset_id}/waveform", response_model=WaveformOut)
async def media_waveform(
    asset_id: uuid.UUID, db: Db, ctx: Ctx, _: Principal = Reader
) -> WaveformOut:
    service = MediaService(db, ctx)
    asset = await service.get(asset_id)
    if asset.waveform_object_id is None:
        raise NotFound("Este vídeo no tiene forma de onda (sin audio)")
    obj = await db.get(StoredObject, asset.waveform_object_id)
    if obj is None or obj.status != "available":
        raise NotFound("Forma de onda no disponible")
    data = json.loads(await ctx.storage.get_bytes(obj.key, max_bytes=2 * 1024 * 1024))
    return WaveformOut.model_validate(data)
