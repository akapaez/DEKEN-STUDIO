from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from deken_api.api.v1.schemas import (
    JobDetailOut,
    JobEventOut,
    JobListOut,
    JobOut,
    JobOutputOut,
)
from deken_api.deps import Ctx, Db, Principal, require
from deken_api.security.rbac import Permission
from deken_api.services.jobs import JobService
from deken_shared.jobs import JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListOut)
async def list_jobs(
    db: Db,
    ctx: Ctx,
    status: JobStatus | None = None,
    type: str | None = Query(default=None, max_length=64),  # noqa: A002
    limit: int = Query(default=50, ge=1, le=200),
    before: uuid.UUID | None = None,
    _: Principal = require(Permission.JOBS_READ),
) -> JobListOut:
    jobs = await JobService(db, ctx).list_jobs(
        status=status, job_type=type, limit=limit, before=before
    )
    return JobListOut(
        items=[JobOut.model_validate(j) for j in jobs],
        next_before=jobs[-1].id if len(jobs) == limit else None,
    )


@router.get("/{job_id}", response_model=JobDetailOut)
async def get_job(
    job_id: uuid.UUID, db: Db, ctx: Ctx, _: Principal = require(Permission.JOBS_READ)
) -> JobDetailOut:
    detail = await JobService(db, ctx).get(job_id)
    return JobDetailOut(
        job=JobOut.model_validate(detail.job),
        events=[JobEventOut.model_validate(e) for e in detail.events],
        outputs=[JobOutputOut.model_validate(o) for o in detail.outputs],
    )


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel_job(
    job_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = require(Permission.JOBS_MANAGE)
) -> JobOut:
    job = await JobService(db, ctx).cancel(job_id, ctx=principal.audit)
    return JobOut.model_validate(job)


@router.post("/{job_id}/retry", response_model=JobOut)
async def retry_job(
    job_id: uuid.UUID, db: Db, ctx: Ctx, principal: Principal = require(Permission.JOBS_MANAGE)
) -> JobOut:
    job = await JobService(db, ctx).retry(job_id, ctx=principal.audit)
    return JobOut.model_validate(job)
