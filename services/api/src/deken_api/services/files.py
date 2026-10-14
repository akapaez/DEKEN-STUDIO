"""Acceso a ficheros almacenados mediante URLs firmadas de corta duración."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.context import AppContext
from deken_api.db.models import StoredObject
from deken_api.errors import Conflict, NotFound
from deken_api.integrations.storage import Audience, PresignedUrl
from deken_api.services import audit
from deken_api.services.audit import AuditContext

_EXTENSIONS = {"video/mp4": "mp4", "image/jpeg": "jpg", "image/png": "png"}
# El nombre deja claro qué es: un autotest sintético o un render de evaluación (no comercial).
_PREFIXES = {"system_test": "autotest-sintetico", "evaluation": "evaluacion-remotion"}


def download_filename(obj: StoredObject) -> str:
    if obj.original_filename:
        return obj.original_filename
    ext = _EXTENSIONS.get(obj.content_type, "bin")
    prefix = _PREFIXES.get(obj.kind, obj.kind)
    return f"deken-{prefix}-{obj.id}.{ext}"


async def get_object(db: AsyncSession, object_id: uuid.UUID) -> StoredObject:
    obj = await db.get(StoredObject, object_id)
    if obj is None or obj.status == "deleted":
        raise NotFound("Fichero no encontrado")
    return obj


async def download_url(
    db: AsyncSession, app: AppContext, ctx: AuditContext, object_id: uuid.UUID
) -> tuple[StoredObject, PresignedUrl]:
    obj = await get_object(db, object_id)
    if obj.status != "available":
        raise Conflict("El fichero no está disponible (no verificado)", code="not_available")
    signed = app.storage.presign_get(
        obj.key,
        audience=Audience.BROWSER,
        ttl_seconds=app.settings.download_url_ttl_seconds,
        download_filename=download_filename(obj),
    )
    audit.record(db, ctx, "file.download_url", target_type="object", target_id=obj.id)
    await db.commit()
    return obj, signed
