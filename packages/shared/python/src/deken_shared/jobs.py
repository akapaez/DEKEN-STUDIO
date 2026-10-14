"""Contrato de trabajos v1 entre la API y los workers (locales o en la nube).

El worker solo abre conexiones salientes HTTPS hacia la API. Recibe URLs firmadas
para leer entradas y las solicita para subir salidas: nunca tiene credenciales de
base de datos ni de almacenamiento.

Cambios incompatibles en este módulo exigen incrementar `JOB_CONTRACT_VERSION`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from deken_shared.media import ImageSpec, VideoSpec

JOB_CONTRACT_VERSION = 1
CONTRACT_HEADER = "X-Deken-Job-Contract"

NAME_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"
ERROR_CODE_PATTERN = r"^[a-z][a-z0-9_]{1,63}$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"

_NAME_RE = re.compile(NAME_PATTERN)


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = frozenset({JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED})


class JobType(StrEnum):
    SYSTEM_RENDER_SELFTEST = "system.render_selftest"
    SYSTEM_REMOTION_EVAL = "system.remotion_eval"
    MEDIA_INGEST = "media.ingest"
    RENDER_TIMELINE = "render.timeline"


class Queue(StrEnum):
    RENDER = "render"
    ANALYSIS = "analysis"


class OutputKind(StrEnum):
    VIDEO = "video"
    IMAGE = "image"
    JSON = "json"
    TEXT = "text"


class ErrorCode(StrEnum):
    """Códigos de error estándar. Los handlers pueden usar otros con el mismo formato."""

    LEASE_EXPIRED = "lease_expired"
    OUTPUT_VERIFICATION_FAILED = "output_verification_failed"
    MISSING_OUTPUT = "missing_output"
    INVALID_PAYLOAD = "invalid_payload"
    UNSUPPORTED_JOB_TYPE = "unsupported_job_type"
    INPUT_UNAVAILABLE = "input_unavailable"
    FFMPEG_FAILED = "ffmpeg_failed"
    LOCAL_VERIFICATION_FAILED = "local_verification_failed"
    TIMEOUT = "timeout"
    UPLOAD_FAILED = "upload_failed"
    WORKER_ERROR = "worker_error"
    INVALID_MEDIA = "invalid_media"
    INVALID_TIMELINE = "invalid_timeline"
    REMOTION_LICENSE_REQUIRED = "remotion_license_required"
    RENDER_FAILED = "render_failed"
    ENGINE_UNAVAILABLE = "engine_unavailable"


# content-type → (tipo de salida, extensión). La extensión nunca viene del worker.
OUTPUT_CONTENT_TYPES: Mapping[str, tuple[OutputKind, str]] = {
    "video/mp4": (OutputKind.VIDEO, "mp4"),
    "image/jpeg": (OutputKind.IMAGE, "jpg"),
    "image/png": (OutputKind.IMAGE, "png"),
    "image/webp": (OutputKind.IMAGE, "webp"),
    "application/json": (OutputKind.JSON, "json"),
    "text/vtt": (OutputKind.TEXT, "vtt"),
}


# --- Payloads por tipo -------------------------------------------------------------


class RenderSelftestPayload(BaseModel):
    """Autotest de render: genera una señal SINTÉTICA (barras + tono) y la verifica.

    No es contenido: sirve para comprobar que la cadena worker → FFmpeg → subida →
    verificación en servidor funciona de extremo a extremo.
    """

    model_config = ConfigDict(extra="forbid")

    duration_s: float = Field(default=3.0, ge=1.0, le=30.0)
    width: int = Field(default=1080, ge=16, le=3840)
    height: int = Field(default=1920, ge=16, le=3840)
    fps: int = Field(default=30, ge=1, le=60)
    label: str = Field(default="AUTOTEST SINTÉTICO", max_length=80)

    def video_spec(self) -> VideoSpec:
        return VideoSpec(
            width=self.width,
            height=self.height,
            fps=self.fps,
            duration_s=self.duration_s,
        )


# --- Entradas firmadas ---------------------------------------------------------------


InputKind = Literal["video", "image", "audio", "font", "document"]
INPUT_KEY_PATTERN = r"^(asset|brand):[0-9a-f-]{36}$"


class InputRef(BaseModel):
    """Objeto autorizado que la API firmará para el worker al reclamar el trabajo.

    Se fija al crear el trabajo (la API ya ha comprobado permisos y estado del medio)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=NAME_PATTERN, description="Nombre del fichero local (sin extensión)")
    object_id: UUID
    kind: InputKind
    extension: str = Field(pattern=r"^[a-z0-9]{1,8}$")
    key: str | None = Field(default=None, pattern=INPUT_KEY_PATTERN)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    duration_s: float | None = Field(default=None, gt=0)
    has_audio: bool | None = None


# --- Payloads de Sprint 1 --------------------------------------------------------------


class ProxyTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(ge=16, le=3840, multiple_of=2)
    height: int = Field(ge=16, le=3840, multiple_of=2)
    fps: float = Field(gt=0, le=120)
    duration_s: float = Field(gt=0)
    has_audio: bool


class MediaIngestPayload(BaseModel):
    """Ingesta de un original: SHA-256, validación por decodificación y derivados."""

    model_config = ConfigDict(extra="forbid")

    asset_id: UUID
    inputs: list[InputRef] = Field(min_length=1, max_length=1)
    proxy: ProxyTarget
    poster_max_px: int = Field(default=720, ge=64, le=2048)
    strip_frames: int = Field(default=10, ge=2, le=40)
    strip_height: int = Field(default=180, ge=60, le=480)
    waveform_points: int = Field(default=1000, ge=100, le=10_000)
    decode_sample_s: float = Field(default=10.0, ge=1.0, le=120.0)

    def proxy_spec(self) -> VideoSpec:
        p = self.proxy
        expected = round(p.duration_s * p.fps)
        return VideoSpec(
            width=p.width,
            height=p.height,
            fps=p.fps,
            duration_s=p.duration_s,
            audio_codec="aac" if p.has_audio else None,
            # Los orígenes de móvil suelen tener cadencia variable: margen del 1 %.
            frame_tolerance=max(2, round(expected * 0.01)),
            container_tolerance_s=max(0.25, p.duration_s * 0.01),
        )


class RemotionEvalPayload(BaseModel):
    """Composición de evaluación técnica de Remotion (5 s, 1080×1920, 30 fps)."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="DEKEN STUDIO AI", min_length=1, max_length=40)
    subtitle: str = Field(default="Motor de composición", min_length=1, max_length=60)
    label: str = Field(default="Evaluación técnica", min_length=1, max_length=40)

    def video_spec(self) -> VideoSpec:
        return VideoSpec(width=1080, height=1920, fps=30, duration_s=5.0, frame_tolerance=0)


RenderPurpose = Literal["evaluation", "production"]


class RenderTimelinePayload(BaseModel):
    """Render de una línea de tiempo `deken.timeline/1` con Remotion.

    La API valida el documento (JSON Schema) y resuelve las referencias a medios
    autorizados en `inputs`; las reglas semánticas las comprueba el motor."""

    model_config = ConfigDict(extra="forbid")

    timeline: dict[str, Any]
    purpose: RenderPurpose = "evaluation"
    inputs: list[InputRef] = Field(default_factory=list, max_length=500)
    title: str | None = Field(default=None, max_length=200)

    def video_spec(self) -> VideoSpec:
        output = self.timeline.get("output") or {}
        fps = float(output.get("fps", 30))
        frames = int(output.get("duration_frames", 1))
        return VideoSpec(
            width=int(output.get("width", 1080)),
            height=int(output.get("height", 1920)),
            fps=fps,
            duration_s=frames / fps,
            frame_tolerance=0,
        )


# --- Registro de tipos ---------------------------------------------------------------


@dataclass(frozen=True)
class OutputSpec:
    kind: OutputKind
    content_type: str
    video_spec: Callable[[BaseModel], VideoSpec] | None = None
    """Para salidas de vídeo: especificación esperada derivada del payload."""
    image_spec: ImageSpec | None = None
    required: bool = True


@dataclass(frozen=True)
class JobTypeSpec:
    job_type: JobType
    queue: Queue
    payload_model: type[BaseModel]
    outputs: Mapping[str, OutputSpec] = field(default_factory=dict)
    """Salidas por nombre. Las `required` deben entregarse todas."""
    default_max_attempts: int = 3
    timeout_s: int = 3600
    storage_kind: str = "derived"
    """Prefijo/clase de almacenamiento de las salidas (`system_test`, `derived`, `render`…)."""
    storage_kind_fn: Callable[[BaseModel], str] | None = None

    def storage_kind_for(self, payload: BaseModel) -> str:
        return self.storage_kind_fn(payload) if self.storage_kind_fn else self.storage_kind


def _video_spec_of(model: type[BaseModel], method: str) -> Callable[[BaseModel], VideoSpec]:
    def _get(payload: BaseModel) -> VideoSpec:
        if not isinstance(payload, model):
            raise TypeError(f"payload no es {model.__name__}")
        result: VideoSpec = getattr(payload, method)()
        return result

    return _get


def _timeline_storage(payload: BaseModel) -> str:
    if not isinstance(payload, RenderTimelinePayload):
        raise TypeError("payload no es RenderTimelinePayload")
    return "render" if payload.purpose == "production" else "evaluation"


THUMBNAIL = ImageSpec(codecs=("mjpeg",))

JOB_TYPES: Mapping[JobType, JobTypeSpec] = {
    JobType.SYSTEM_RENDER_SELFTEST: JobTypeSpec(
        job_type=JobType.SYSTEM_RENDER_SELFTEST,
        queue=Queue.RENDER,
        payload_model=RenderSelftestPayload,
        outputs={
            "video": OutputSpec(
                kind=OutputKind.VIDEO,
                content_type="video/mp4",
                video_spec=_video_spec_of(RenderSelftestPayload, "video_spec"),
            )
        },
        default_max_attempts=2,
        timeout_s=300,
        storage_kind="system_test",
    ),
    JobType.SYSTEM_REMOTION_EVAL: JobTypeSpec(
        job_type=JobType.SYSTEM_REMOTION_EVAL,
        queue=Queue.RENDER,
        payload_model=RemotionEvalPayload,
        outputs={
            "video": OutputSpec(
                kind=OutputKind.VIDEO,
                content_type="video/mp4",
                video_spec=_video_spec_of(RemotionEvalPayload, "video_spec"),
            )
        },
        default_max_attempts=2,
        timeout_s=900,
        storage_kind="evaluation",
    ),
    JobType.MEDIA_INGEST: JobTypeSpec(
        job_type=JobType.MEDIA_INGEST,
        queue=Queue.ANALYSIS,
        payload_model=MediaIngestPayload,
        outputs={
            "poster": OutputSpec(
                kind=OutputKind.IMAGE, content_type="image/jpeg", image_spec=THUMBNAIL
            ),
            "strip": OutputSpec(
                kind=OutputKind.IMAGE, content_type="image/jpeg", image_spec=THUMBNAIL
            ),
            "proxy": OutputSpec(
                kind=OutputKind.VIDEO,
                content_type="video/mp4",
                video_spec=_video_spec_of(MediaIngestPayload, "proxy_spec"),
            ),
            "waveform": OutputSpec(
                kind=OutputKind.JSON, content_type="application/json", required=False
            ),
        },
        default_max_attempts=3,
        timeout_s=6 * 3600,
        storage_kind="derived",
    ),
    JobType.RENDER_TIMELINE: JobTypeSpec(
        job_type=JobType.RENDER_TIMELINE,
        queue=Queue.RENDER,
        payload_model=RenderTimelinePayload,
        outputs={
            "video": OutputSpec(
                kind=OutputKind.VIDEO,
                content_type="video/mp4",
                video_spec=_video_spec_of(RenderTimelinePayload, "video_spec"),
            )
        },
        default_max_attempts=2,
        timeout_s=6 * 3600,
        storage_kind="evaluation",
        storage_kind_fn=_timeline_storage,
    ),
}


def get_job_type_spec(job_type: str) -> JobTypeSpec:
    try:
        return JOB_TYPES[JobType(job_type)]
    except ValueError as exc:
        raise KeyError(job_type) from exc


def is_valid_output_name(name: str) -> bool:
    return bool(_NAME_RE.fullmatch(name))


# --- Mensajes del protocolo -----------------------------------------------------------


class _Msg(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkerCapabilities(_Msg):
    engines: dict[str, str] = Field(default_factory=dict, max_length=20)
    """Motores disponibles y su versión (p. ej. remotion, node, licencia de Remotion)."""
    ffmpeg_version: str | None = Field(default=None, max_length=200)
    ffprobe_version: str | None = Field(default=None, max_length=200)
    encoders: list[str] = Field(default_factory=list, max_length=200)
    hwaccels: list[str] = Field(default_factory=list, max_length=50)
    job_types: list[str] = Field(default_factory=list, max_length=100)
    max_concurrency: int = Field(default=1, ge=1, le=64)


class WorkerHeartbeat(_Msg):
    hostname: str = Field(max_length=255)
    platform: str = Field(max_length=255)
    version: str = Field(max_length=50)
    capabilities: WorkerCapabilities


class WorkerHeartbeatAck(_Msg):
    worker_id: UUID
    name: str
    queues: list[str]
    contract_version: int
    server_time: datetime


class ClaimRequest(_Msg):
    queues: list[Queue] = Field(min_length=1, max_length=10)
    job_types: list[str] = Field(min_length=1, max_length=100)
    wait_seconds: int = Field(default=20, ge=0, le=30)


class JobInput(_Msg):
    name: str
    object_id: UUID
    url: str
    content_type: str
    size_bytes: int | None
    sha256: str | None
    expires_at: datetime
    kind: str | None = None
    extension: str | None = None
    key: str | None = None
    width: int | None = None
    height: int | None = None
    duration_s: float | None = None
    has_audio: bool | None = None


class ClaimedJob(_Msg):
    id: UUID
    type: str
    queue: str
    attempt: int
    max_attempts: int
    payload: dict[str, Any]
    inputs: list[JobInput]
    lease_seconds: int
    lease_expires_at: datetime
    timeout_s: int
    contract_version: int = JOB_CONTRACT_VERSION


class ProgressReport(_Msg):
    progress: float = Field(ge=0.0, le=1.0)
    message: str | None = Field(default=None, max_length=500)


class LeaseAck(_Msg):
    cancel_requested: bool
    lease_expires_at: datetime


class OutputUploadRequest(_Msg):
    name: str = Field(pattern=NAME_PATTERN)
    content_type: str = Field(max_length=100)
    size_bytes: int = Field(gt=0)


class OutputUploadTicket(_Msg):
    object_id: UUID
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str]
    expires_at: datetime


class OutputDeclaration(_Msg):
    name: str = Field(pattern=NAME_PATTERN)
    object_id: UUID
    sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(gt=0)


class CompleteRequest(_Msg):
    outputs: list[OutputDeclaration] = Field(max_length=100)
    result: dict[str, Any] = Field(default_factory=dict)


class FailRequest(_Msg):
    code: str = Field(pattern=ERROR_CODE_PATTERN)
    message: str = Field(max_length=2000)
    retryable: bool = False
    details: dict[str, Any] | None = None


class JobTransitionAck(_Msg):
    id: UUID
    status: JobStatus
