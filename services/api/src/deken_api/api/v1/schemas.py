"""Esquemas de entrada/salida de la API v1 (contrato público con la web)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from deken_api.security.rbac import Permission, Role
from deken_api.services.auth import validate_email
from deken_shared.jobs import JobStatus, Queue


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


Email = Annotated[str, Field(min_length=3, max_length=320), AfterValidator(validate_email)]


# --- Auth -------------------------------------------------------------------------------


class LoginRequest(_In):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class UserOut(_Out):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class MeOut(BaseModel):
    user: UserOut
    permissions: list[Permission]
    session_expires_at: datetime
    csrf_token: str


class PasswordChangeRequest(_In):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


# --- Usuarios ----------------------------------------------------------------------------


class UserCreateRequest(_In):
    email: Email
    full_name: str = Field(min_length=1, max_length=200)
    role: Role
    password: str = Field(min_length=1, max_length=256)


class UserUpdateRequest(_In):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Role | None = None
    is_active: bool | None = None


class UserPasswordResetRequest(_In):
    password: str = Field(min_length=1, max_length=256)


class RoleInfo(BaseModel):
    role: Role
    label: str
    permissions: list[Permission]


# --- Workers -----------------------------------------------------------------------------


class WorkerOut(_Out):
    id: uuid.UUID
    name: str
    token_prefix: str
    status: Literal["active", "revoked"]
    queues: list[str]
    capabilities: dict[str, Any]
    version: str | None
    hostname: str | None
    platform: str | None
    last_seen_at: datetime | None
    online: bool = False
    created_at: datetime
    revoked_at: datetime | None


class WorkerCreateRequest(_In):
    name: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9 ._-]*$")
    queues: list[Queue] = Field(min_length=1, max_length=10)


class WorkerCreatedOut(BaseModel):
    worker: WorkerOut
    token: str = Field(description="Se muestra una sola vez. Guárdalo en el worker.")


# --- Ficheros y trabajos -------------------------------------------------------------------


class StoredObjectOut(_Out):
    id: uuid.UUID
    kind: str
    status: str
    content_type: str
    size_bytes: int | None
    sha256: str | None
    media_info: dict[str, Any] | None
    created_at: datetime
    verified_at: datetime | None


class DownloadUrlOut(BaseModel):
    url: str
    expires_at: datetime
    filename: str


class JobOut(_Out):
    id: uuid.UUID
    type: str
    queue: str
    status: JobStatus
    priority: int
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: dict[str, Any] | None
    progress: float
    progress_message: str | None
    attempts: int
    max_attempts: int
    cancel_requested: bool
    lease_owner_id: uuid.UUID | None
    run_after: datetime
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobEventOut(_Out):
    id: int
    occurred_at: datetime
    kind: str
    attempt: int
    message: str | None
    data: dict[str, Any]


class JobOutputOut(_Out):
    name: str
    attempt: int
    kind: str
    verified: bool
    verification: dict[str, Any] | None
    stored_object: StoredObjectOut


class JobDetailOut(BaseModel):
    job: JobOut
    events: list[JobEventOut]
    outputs: list[JobOutputOut]


class JobListOut(BaseModel):
    items: list[JobOut]
    next_before: uuid.UUID | None


class SelftestRequest(_In):
    duration_s: float = Field(default=3.0, ge=1.0, le=30.0)


# --- Auditoría ----------------------------------------------------------------------------


class AuditEventOut(_Out):
    id: int
    occurred_at: datetime
    actor_type: str
    actor_id: uuid.UUID | None
    actor_label: str | None
    action: str
    outcome: str
    target_type: str | None
    target_id: str | None
    ip: str | None
    request_id: str | None
    details: dict[str, Any]


class AuditListOut(BaseModel):
    items: list[AuditEventOut]
    next_before: int | None


# --- Sistema -----------------------------------------------------------------------------


class CheckOut(BaseModel):
    status: Literal["ok", "error"]
    latency_ms: float | None = None
    error: str | None = None
    migration: str | None = None
    bucket: str | None = None


class HealthOut(BaseModel):
    status: Literal["ok", "degraded", "error"]
    checks: dict[str, Literal["ok", "error"]]


class FfprobeStatus(BaseModel):
    available: bool
    version: str | None


class WorkersStatus(BaseModel):
    active: int
    online: int
    online_names: list[str]


class JobsStatus(BaseModel):
    by_status: dict[str, int]
    failed_last_24h: int


class AiStatus(BaseModel):
    configured: bool
    provider: str | None


class SystemStatusOut(BaseModel):
    status: Literal["ok", "degraded", "error"]
    version: str
    environment: str
    server_time: datetime
    checks: dict[str, CheckOut]
    ffprobe: FfprobeStatus
    workers: WorkersStatus
    jobs: JobsStatus
    ai: AiStatus
