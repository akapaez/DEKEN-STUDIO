"""Gestión de workers por administradores (alta, revocación, estado)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from deken_api.api.v1.schemas import WorkerCreatedOut, WorkerCreateRequest, WorkerOut
from deken_api.db.models import Worker
from deken_api.deps import Ctx, Db, Principal, require
from deken_api.security.rbac import Permission
from deken_api.services import workers as workers_service

router = APIRouter(prefix="/workers", tags=["workers"])

Admin = require(Permission.WORKERS_MANAGE)


def worker_out(worker: Worker, threshold: int) -> WorkerOut:
    out = WorkerOut.model_validate(worker)
    out.online = workers_service.is_online(worker, threshold_seconds=threshold)
    return out


@router.get("", response_model=list[WorkerOut])
async def list_workers(
    db: Db, ctx: Ctx, _: Principal = require(Permission.SYSTEM_READ)
) -> list[WorkerOut]:
    threshold = ctx.settings.worker_online_seconds
    return [worker_out(w, threshold) for w in await workers_service.list_workers(db)]


@router.post("", response_model=WorkerCreatedOut, status_code=status.HTTP_201_CREATED)
async def register_worker(
    body: WorkerCreateRequest, db: Db, ctx: Ctx, principal: Principal = Admin
) -> WorkerCreatedOut:
    registered = await workers_service.register_worker(
        db, principal.audit, name=body.name, queues=body.queues
    )
    return WorkerCreatedOut(
        worker=worker_out(registered.worker, ctx.settings.worker_online_seconds),
        token=registered.token,
    )


@router.post("/{worker_id}/revoke", response_model=WorkerOut)
async def revoke_worker(
    worker_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = Admin
) -> WorkerOut:
    worker = await workers_service.revoke_worker(db, principal.audit, worker_id)
    return worker_out(worker, ctx.settings.worker_online_seconds)
