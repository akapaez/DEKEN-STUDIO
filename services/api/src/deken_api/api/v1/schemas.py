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


class RemotionStatus(BaseModel):
    license_mode: Literal["evaluation", "company"]
    commercial_renders_enabled: bool


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
    remotion: RemotionStatus


# --- Biblioteca audiovisual (Sprint 1) ------------------------------------------------------

MediaStatus = Literal[
    "uploading", "processing", "ready", "rejected", "failed", "duplicate", "cancelled"
]
PeoplePresent = Literal["yes", "no", "unknown"]
ConsentStatus = Literal["not_required", "pending", "granted", "denied"]


class MediaUploadRequest(_In):
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)
    content_type: str = Field(default="", max_length=100)
    title: str | None = Field(default=None, max_length=200)


class MediaUploadOut(BaseModel):
    asset_id: uuid.UUID
    part_size_bytes: int
    part_count: int
    max_parts_per_request: int


class PartUrlsRequest(_In):
    part_numbers: list[int] = Field(min_length=1, max_length=1000)


class PartUrlOut(BaseModel):
    part_number: int
    url: str


class MediaAssetOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    original_filename: str
    status: MediaStatus
    status_reason: str | None
    declared_size_bytes: int
    sha256: str | None
    duplicate_of_id: uuid.UUID | None
    container: str | None
    duration_s: float | None
    width: int | None
    height: int | None
    orientation: str | None
    rotation: int | None
    fps: float | None
    video_codec: str | None
    audio_codec: str | None
    has_audio: bool | None
    tags: list[str]
    recorded_at: datetime | None
    location: str | None
    people_present: PeoplePresent
    consent_status: ConsentStatus
    consent_reference: str | None
    usage_restrictions: str | None
    rights_owner: str
    rights_updated_at: datetime | None
    usable_for_production: bool
    ingest_job_id: uuid.UUID | None
    poster_url: str | None
    strip_url: str | None
    strip_frames: int | None
    created_at: datetime
    archived_at: datetime | None


class MediaAssetDetailOut(MediaAssetOut):
    proxy_url: str | None
    has_waveform: bool
    original_object: StoredObjectOut | None
    derivatives: dict[str, StoredObjectOut]
    probe: dict[str, Any] | None


class MediaListOut(BaseModel):
    items: list[MediaAssetOut]
    total: int


class MediaUpdateRequest(_In):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=30)
    recorded_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)


class MediaRightsRequest(_In):
    people_present: PeoplePresent | None = None
    consent_status: ConsentStatus | None = None
    consent_reference: str | None = Field(default=None, max_length=300)
    usage_restrictions: str | None = Field(default=None, max_length=4000)
    rights_owner: str | None = Field(default=None, min_length=1, max_length=200)


class TagCountOut(BaseModel):
    tag: str
    count: int


class WaveformOut(BaseModel):
    version: int
    duration_s: float
    peaks: list[float]


# --- Marca DEKEN (Sprint 1) -------------------------------------------------------------------

BrandKind = Literal["logo", "font", "image"]
Background = Literal["dark", "light", "any"]


class BrandUploadRequest(_In):
    kind: BrandKind
    name: str = Field(min_length=1, max_length=200)
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)
    declared_color: str | None = Field(default=None, max_length=32, pattern=r"^[a-z]+(-[a-z]+)?$")
    family: str | None = Field(default=None, max_length=64)
    license_ref: str | None = Field(default=None, max_length=200)


class BrandUploadOut(BaseModel):
    asset_id: uuid.UUID
    upload_url: str
    headers: dict[str, str]


class BrandAssetOut(BaseModel):
    id: uuid.UUID
    kind: BrandKind
    name: str
    family: str | None
    status: str
    status_reason: str | None
    original_filename: str
    width: int | None
    height: int | None
    aspect_ratio: float | None
    has_alpha: bool | None
    declared_color: str | None
    measured_color_name: str | None
    measured_color_hex: str | None
    color_mismatch: bool
    recommended_background: Background | None
    usage_background: Background | None
    font_family: str | None
    font_style: str | None
    font_weight: int | None
    license_ref: str | None
    notes: str | None
    analysis: dict[str, Any] | None
    preview_url: str | None
    created_at: datetime


class BrandUpdateRequest(_In):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    usage_background: Background | None = None
    family: str | None = Field(default=None, max_length=64)
    declared_color: str | None = Field(default=None, max_length=32, pattern=r"^[a-z]+(-[a-z]+)?$")
    notes: str | None = Field(default=None, max_length=2000)
    license_ref: str | None = Field(default=None, max_length=200)


# --- Renders con Remotion -------------------------------------------------------------------


class RemotionEvalRequest(_In):
    title: str = Field(default="DEKEN STUDIO AI", min_length=1, max_length=40)
    subtitle: str = Field(default="Motor de composición", min_length=1, max_length=60)


class TimelineRenderRequest(_In):
    timeline: dict[str, Any]
    purpose: Literal["evaluation", "production"] = "evaluation"
    title: str | None = Field(default=None, max_length=200)


class RenderEngineOut(BaseModel):
    engine: Literal["remotion"]
    license_mode: Literal["evaluation", "company"]
    commercial_renders_enabled: bool
    workers_with_remotion: list[str]
    note: str
