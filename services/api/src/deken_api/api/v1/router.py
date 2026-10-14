from __future__ import annotations

from fastapi import APIRouter

from deken_api.api.v1 import audit, auth, files, jobs, system, users, worker_protocol, workers

API_PREFIX = "/api/v1"

router = APIRouter(prefix=API_PREFIX)
for module in (system, auth, users, workers, worker_protocol, jobs, files, audit):
    router.include_router(module.router)
