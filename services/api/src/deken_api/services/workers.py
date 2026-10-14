"""Registro y autenticación de workers (procesadores locales o en la nube)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.db.models import Worker
from deken_api.errors import Conflict, NotFound
from deken_api.security.tokens import WORKER_TOKEN_PREFIX, hash_token, new_worker_token
from deken_api.services import audit
from deken_api.services.audit import AuditContext
from deken_shared.jobs import Queue, WorkerHeartbeat


@dataclass(frozen=True)
class RegisteredWorker:
    worker: Worker
    token: str


def is_online(worker: Worker, *, threshold_seconds: int, now: datetime | None = None) -> bool:
    if worker.status != "active" or worker.last_seen_at is None:
        return False
    now = now or datetime.now(UTC)
    return now - worker.last_seen_at <= timedelta(seconds=threshold_seconds)


async def list_workers(db: AsyncSession) -> list[Worker]:
    return list((await db.execute(select(Worker).order_by(Worker.created_at))).scalars())


async def register_worker(
    db: AsyncSession, ctx: AuditContext, *, name: str, queues: list[Queue]
) -> RegisteredWorker:
    name = name.strip()
    taken = await db.scalar(select(func.count()).select_from(Worker).where(Worker.name == name))
    if taken:
        raise Conflict("Ya existe un worker con ese nombre", code="worker_name_taken")
    token = new_worker_token()
    worker = Worker(
        name=name,
        token_prefix=token[len(WORKER_TOKEN_PREFIX) : len(WORKER_TOKEN_PREFIX) + 8],
        token_hash=hash_token(token),
        queues=sorted({q.value for q in queues}),
        created_by_user_id=ctx.actor.id,
    )
    db.add(worker)
    await db.flush()
    audit.record(
        db,
        ctx,
        "worker.register",
        target_type="worker",
        target_id=worker.id,
        details={"name": name, "queues": worker.queues},
    )
    await db.commit()
    return RegisteredWorker(worker=worker, token=token)


async def revoke_worker(db: AsyncSession, ctx: AuditContext, worker_id: uuid.UUID) -> Worker:
    worker = (
        await db.execute(select(Worker).where(Worker.id == worker_id).with_for_update())
    ).scalar_one_or_none()
    if worker is None:
        raise NotFound("Worker no encontrado")
    if worker.status == "revoked":
        raise Conflict("El worker ya está revocado")
    worker.status = "revoked"
    worker.revoked_at = datetime.now(UTC)
    audit.record(db, ctx, "worker.revoke", target_type="worker", target_id=worker.id)
    await db.commit()
    return worker


async def authenticate_worker(db: AsyncSession, token: str) -> Worker | None:
    if not token.startswith(WORKER_TOKEN_PREFIX):
        return None
    worker = (
        await db.execute(select(Worker).where(Worker.token_hash == hash_token(token)))
    ).scalar_one_or_none()
    if worker is None or worker.status != "active":
        return None
    return worker


async def heartbeat(db: AsyncSession, worker: Worker, hb: WorkerHeartbeat) -> Worker:
    worker.hostname = hb.hostname
    worker.platform = hb.platform
    worker.version = hb.version
    worker.capabilities = hb.capabilities.model_dump(mode="json")
    worker.last_seen_at = datetime.now(UTC)
    await db.commit()
    return worker
