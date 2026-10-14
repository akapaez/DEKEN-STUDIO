"""Efectos de dominio cuando un trabajo termina o vuelve a la cola.

Se ejecutan dentro de la transacción del cambio de estado del trabajo, de modo que el
estado del trabajo y el del objeto de negocio nunca quedan desalineados.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.context import AppContext
from deken_api.db.models import Job
from deken_shared.jobs import JobType


async def on_terminal(db: AsyncSession, app: AppContext, job: Job) -> None:
    if job.type == JobType.MEDIA_INGEST.value:
        from deken_api.services.media import MediaService

        await MediaService(db, app).ingest_finished(job)


async def on_requeued(db: AsyncSession, app: AppContext, job: Job) -> None:
    if job.type == JobType.MEDIA_INGEST.value:
        from deken_api.services.media import MediaService

        await MediaService(db, app).ingest_requeued(job)
