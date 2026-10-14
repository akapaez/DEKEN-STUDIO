from __future__ import annotations

import uuid

from fastapi import APIRouter

from deken_api.api.v1.schemas import DownloadUrlOut
from deken_api.deps import Ctx, Db, Principal, require
from deken_api.security.rbac import Permission
from deken_api.services import files as files_service

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{object_id}/download-url", response_model=DownloadUrlOut)
async def download_url(
    object_id: uuid.UUID,
    db: Db,
    ctx: Ctx,
    principal: Principal = require(Permission.FILES_READ),
) -> DownloadUrlOut:
    """URL firmada de corta duración. Solo para ficheros verificados."""
    obj, signed = await files_service.download_url(db, ctx, principal.audit, object_id)
    return DownloadUrlOut(
        url=signed.url,
        expires_at=signed.expires_at,
        filename=files_service.download_filename(obj),
    )
