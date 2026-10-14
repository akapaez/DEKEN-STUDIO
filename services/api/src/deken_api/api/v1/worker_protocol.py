"""Protocolo de workers v1 (autenticación Bearer con token de worker).

Todas las llamadas las inicia el worker (conexiones salientes). Ver docs/CONTRACTS.md §3.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status

from deken_api.deps import Ctx, CurrentWorker, Db
from deken_api.services import workers as workers_service
from deken_api.services.jobs import JobService
from deken_shared.jobs import (
    JOB_CONTRACT_VERSION,
    ClaimedJob,
    ClaimRequest,
    CompleteRequest,
    FailRequest,
    JobStatus,
    JobTransitionAck,
    LeaseAck,
    OutputUploadRequest,
    OutputUploadTicket,
    ProgressReport,
    WorkerHeartbeat,
    WorkerHeartbeatAck,
)

router = APIRouter(prefix="/worker", tags=["worker-protocol"])


@router.post("/heartbeat", response_model=WorkerHeartbeatAck)
async def heartbeat(body: WorkerHeartbeat, worker: CurrentWorker, db: Db) -> WorkerHeartbeatAck:
    worker = await workers_service.heartbeat(db, worker, body)
    return WorkerHeartbeatAck(
        worker_id=worker.id,
        name=worker.name,
        queues=worker.queues,
        contract_version=JOB_CONTRACT_VERSION,
        server_time=datetime.now(UTC),
    )


@router.post(
    "/jobs/claim",
    response_model=ClaimedJob,
    responses={204: {"description": "No hay trabajos disponibles en el tiempo de espera"}},
)
async def claim(
    body: ClaimRequest, request: Request, worker: CurrentWorker, db: Db, ctx: Ctx
) -> ClaimedJob | Response:
    job = await JobService(db, ctx).claim(worker, body, is_disconnected=request.is_disconnected)
    if job is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return job


@router.post("/jobs/{job_id}/progress", response_model=LeaseAck)
async def progress(
    job_id: uuid.UUID, body: ProgressReport, worker: CurrentWorker, db: Db, ctx: Ctx
) -> LeaseAck:
    return await JobService(db, ctx).progress(job_id, worker, body)


@router.post("/jobs/{job_id}/outputs", response_model=OutputUploadTicket)
async def request_output(
    job_id: uuid.UUID, body: OutputUploadRequest, worker: CurrentWorker, db: Db, ctx: Ctx
) -> OutputUploadTicket:
    return await JobService(db, ctx).request_output(job_id, worker, body)


@router.post("/jobs/{job_id}/complete", response_model=JobTransitionAck)
async def complete(
    job_id: uuid.UUID, body: CompleteRequest, worker: CurrentWorker, db: Db, ctx: Ctx
) -> JobTransitionAck:
    job = await JobService(db, ctx).complete(job_id, worker, body)
    return JobTransitionAck(id=job.id, status=JobStatus(job.status))


@router.post("/jobs/{job_id}/fail", response_model=JobTransitionAck)
async def fail(
    job_id: uuid.UUID, body: FailRequest, worker: CurrentWorker, db: Db, ctx: Ctx
) -> JobTransitionAck:
    job = await JobService(db, ctx).fail(job_id, worker, body)
    return JobTransitionAck(id=job.id, status=JobStatus(job.status))


@router.post("/jobs/{job_id}/cancelled", response_model=JobTransitionAck)
async def cancelled(job_id: uuid.UUID, worker: CurrentWorker, db: Db, ctx: Ctx) -> JobTransitionAck:
    job = await JobService(db, ctx).ack_cancel(job_id, worker)
    return JobTransitionAck(id=job.id, status=JobStatus(job.status))
