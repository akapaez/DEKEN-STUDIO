"""Cola de trabajos: PostgreSQL es la fuente de verdad, Redis solo despierta a los workers.

Máquina de estados (ver ARCHITECTURE.md §7):
    queued → processing → completed | failed | cancelled
    processing → queued   (fallo reintentable o lease expirado, con backoff)
    failed/cancelled → queued (reintento manual)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from deken_api.context import AppContext
from deken_api.db.models import Job, JobEvent, JobOutput, StoredObject, Worker
from deken_api.errors import ApiError, Conflict, NotFound, PermissionDenied
from deken_api.integrations.ffprobe import ProbeError, probe_url
from deken_api.integrations.storage import Audience, StorageError, build_object_key
from deken_api.logs import get_logger
from deken_api.services import audit
from deken_api.services.audit import AuditContext
from deken_shared.jobs import (
    JOB_CONTRACT_VERSION,
    OUTPUT_CONTENT_TYPES,
    TERMINAL_STATUSES,
    ClaimedJob,
    ClaimRequest,
    CompleteRequest,
    ErrorCode,
    FailRequest,
    InputRef,
    JobInput,
    JobStatus,
    JobTypeSpec,
    LeaseAck,
    OutputKind,
    OutputUploadRequest,
    OutputUploadTicket,
    ProgressReport,
    get_job_type_spec,
)
from deken_shared.media import ImageSpec, check_image_spec, check_video_spec

log = get_logger(__name__)

WAKE_KEY = "jobs:wake:{queue}"
MAX_RESULT_BYTES = 64 * 1024
MAX_JSON_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_BACKOFF_SECONDS = 3600
WAIT_SLICE_SECONDS = 5.0


def _now() -> datetime:
    return datetime.now(UTC)


def backoff_seconds(base: int, attempt: int) -> int:
    return int(min(MAX_BACKOFF_SECONDS, base * (2 ** max(0, attempt - 1))))


@dataclass(frozen=True)
class JobDetail:
    job: Job
    events: list[JobEvent]
    outputs: list[JobOutput]


class JobService:
    def __init__(self, db: AsyncSession, app: AppContext) -> None:
        self.db = db
        self.app = app
        self.settings = app.settings

    # --- Utilidades -------------------------------------------------------------------

    def _event(
        self,
        job: Job,
        kind: str,
        message: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.db.add(
            JobEvent(
                job_id=job.id,
                kind=kind,
                attempt=job.attempts,
                message=message,
                data=data or {},
            )
        )

    async def _wake(self, *queues: str) -> None:
        for queue in set(queues):
            key = WAKE_KEY.format(queue=queue)
            try:
                async with self.app.redis.pipeline(transaction=False) as pipe:
                    pipe.lpush(key, "1")
                    pipe.ltrim(key, 0, 99)
                    pipe.expire(key, 3600)
                    await pipe.execute()
            except RedisError as exc:  # los workers siguen sondeando la BD
                log.warning("jobs.wake_failed", queue=queue, error=str(exc))

    def _spec(self, job_type: str) -> JobTypeSpec:
        try:
            return get_job_type_spec(job_type)
        except KeyError:
            raise ApiError(
                f"Tipo de trabajo desconocido: {job_type}",
                code="unknown_job_type",
                status_code=422,
            ) from None

    def _schedule_retry(self, job: Job, error: dict[str, Any], now: datetime) -> None:
        delay = backoff_seconds(self.settings.job_retry_base_seconds, job.attempts)
        job.status = JobStatus.QUEUED.value
        job.run_after = now + timedelta(seconds=delay)
        job.lease_owner_id = None
        job.lease_expires_at = None
        job.error = error
        self._event(
            job,
            "retry_scheduled",
            f"Reintento {job.attempts + 1}/{job.max_attempts} en {delay}s",
            {"delay_s": delay, "error": error},
        )

    async def _finish(self, job: Job, status: JobStatus, now: datetime) -> None:
        job.status = status.value
        job.finished_at = now
        job.lease_owner_id = None
        job.lease_expires_at = None
        # Efectos de dominio (p. ej. estado del activo de la biblioteca) en la misma
        # transacción que el cambio de estado del trabajo.
        from deken_api.services import job_hooks

        await job_hooks.on_terminal(self.db, self.app, job)

    # --- Creación y consulta (usuarios) -------------------------------------------------

    async def create(
        self,
        job_type: str,
        payload: dict[str, Any],
        *,
        ctx: AuditContext,
        priority: int = 0,
        commit: bool = True,
    ) -> Job:
        """Crea un trabajo. Con `commit=False` queda en la transacción del llamante, que
        debe confirmar y después llamar a `wake(job.queue)`."""
        spec = self._spec(job_type)
        try:
            validated = spec.payload_model.model_validate(payload)
        except ValidationError as exc:
            raise ApiError(
                "Payload no válido para el tipo de trabajo",
                code="invalid_payload",
                status_code=422,
                details=json.loads(exc.json(include_url=False)),
            ) from exc
        job = Job(
            type=spec.job_type.value,
            queue=spec.queue.value,
            payload=validated.model_dump(mode="json"),
            priority=priority,
            max_attempts=spec.default_max_attempts,
            timeout_s=spec.timeout_s,
            contract_version=JOB_CONTRACT_VERSION,
            created_by_user_id=ctx.actor.id if ctx.actor.type == "user" else None,
            status=JobStatus.QUEUED.value,
            attempts=0,
            progress=0.0,
            cancel_requested=False,
            run_after=_now(),
        )
        self.db.add(job)
        await self.db.flush()
        self._event(job, "created", "Trabajo creado", {"type": job.type, "queue": job.queue})
        audit.record(
            self.db,
            ctx,
            "job.create",
            target_type="job",
            target_id=job.id,
            details={"type": job.type},
        )
        if commit:
            await self.db.commit()
            await self._wake(job.queue)
        return job

    async def wake(self, queue: str) -> None:
        await self._wake(queue)

    async def list_jobs(
        self,
        *,
        status: JobStatus | None = None,
        job_type: str | None = None,
        limit: int = 50,
        before: uuid.UUID | None = None,
    ) -> list[Job]:
        stmt = select(Job)
        if status is not None:
            stmt = stmt.where(Job.status == status.value)
        if job_type is not None:
            stmt = stmt.where(Job.type == job_type)
        if before is not None:
            ref = await self.db.get(Job, before)
            if ref is not None:
                stmt = stmt.where(
                    or_(
                        Job.created_at < ref.created_at,
                        and_(Job.created_at == ref.created_at, Job.id < ref.id),
                    )
                )
        stmt = stmt.order_by(Job.created_at.desc(), Job.id.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars())

    async def get(self, job_id: uuid.UUID) -> JobDetail:
        job = await self.db.get(Job, job_id)
        if job is None:
            raise NotFound("Trabajo no encontrado")
        events = list(
            (
                await self.db.execute(
                    select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.id)
                )
            ).scalars()
        )
        outputs = list(
            (
                await self.db.execute(
                    select(JobOutput)
                    .where(JobOutput.job_id == job_id)
                    .order_by(JobOutput.attempt, JobOutput.name)
                )
            ).scalars()
        )
        return JobDetail(job=job, events=events, outputs=outputs)

    async def counts(self) -> dict[str, int]:
        rows = await self.db.execute(select(Job.status, func.count()).group_by(Job.status))
        counts = {s.value: 0 for s in JobStatus}
        for status, count in rows.all():
            counts[str(status)] = int(count)
        return counts

    async def failed_since(self, since: datetime) -> int:
        count = await self.db.scalar(
            select(func.count())
            .select_from(Job)
            .where(Job.status == JobStatus.FAILED.value, Job.finished_at >= since)
        )
        return int(count or 0)

    async def _lock(self, job_id: uuid.UUID) -> Job:
        job = (
            await self.db.execute(select(Job).where(Job.id == job_id).with_for_update())
        ).scalar_one_or_none()
        if job is None:
            raise NotFound("Trabajo no encontrado")
        return job

    async def cancel(self, job_id: uuid.UUID, *, ctx: AuditContext) -> Job:
        job = await self._lock(job_id)
        now = _now()
        if job.status == JobStatus.QUEUED.value:
            await self._finish(job, JobStatus.CANCELLED, now)
            self._event(job, "cancelled", "Cancelado antes de empezar")
        elif job.status == JobStatus.PROCESSING.value:
            if not job.cancel_requested:
                job.cancel_requested = True
                self._event(job, "cancel_requested", "Cancelación solicitada al worker")
        else:
            raise Conflict("El trabajo ya ha terminado", code="job_finished")
        audit.record(self.db, ctx, "job.cancel", target_type="job", target_id=job.id)
        await self.db.commit()
        return job

    async def retry(self, job_id: uuid.UUID, *, ctx: AuditContext) -> Job:
        job = await self._lock(job_id)
        if job.status not in {JobStatus.FAILED.value, JobStatus.CANCELLED.value}:
            raise Conflict(
                "Solo se pueden reintentar trabajos fallidos o cancelados",
                code="job_not_retryable",
            )
        previous = job.status
        job.status = JobStatus.QUEUED.value
        job.attempts = 0
        job.error = None
        job.result = None
        job.progress = 0.0
        job.progress_message = None
        job.cancel_requested = False
        job.run_after = _now()
        job.started_at = None
        job.finished_at = None
        self._event(job, "manual_retry", "Reintento manual", {"previous_status": previous})
        audit.record(self.db, ctx, "job.retry", target_type="job", target_id=job.id)
        from deken_api.services import job_hooks

        await job_hooks.on_requeued(self.db, self.app, job)
        await self.db.commit()
        await self._wake(job.queue)
        return job

    # --- Protocolo de workers ----------------------------------------------------------

    async def claim(
        self,
        worker: Worker,
        req: ClaimRequest,
        *,
        is_disconnected: Callable[[], Awaitable[bool]] | None = None,
    ) -> ClaimedJob | None:
        queues = sorted({q.value for q in req.queues} & set(worker.queues))
        if not queues:
            raise PermissionDenied(
                "El worker no tiene permiso para esas colas", code="queue_not_allowed"
            )
        # Se capturan id y nombre: tras cada transacción vacía no se vuelve a leer el ORM.
        worker_id, worker_name = worker.id, worker.name
        await self.db.execute(
            update(Worker).where(Worker.id == worker_id).values(last_seen_at=_now())
        )
        await self.db.commit()
        deadline = time.monotonic() + req.wait_seconds
        while True:
            if is_disconnected is not None and await is_disconnected():
                return None
            job = await self._try_claim(worker_id, worker_name, queues, req.job_types)
            if job is not None:
                return await self._claimed(job)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            await self._wait_signal(queues, min(remaining, WAIT_SLICE_SECONDS))

    async def _wait_signal(self, queues: Sequence[str], wait_s: float) -> None:
        keys = [WAKE_KEY.format(queue=q) for q in queues]
        try:
            await self.app.redis.blpop(keys, timeout=max(0.1, wait_s))
        except RedisError:
            await asyncio.sleep(min(wait_s, 2.0))

    async def _try_claim(
        self,
        worker_id: uuid.UUID,
        worker_name: str,
        queues: Sequence[str],
        job_types: Sequence[str],
    ) -> Job | None:
        now = _now()
        stmt = (
            select(Job)
            .where(
                Job.status == JobStatus.QUEUED.value,
                Job.queue.in_(queues),
                Job.type.in_(list(job_types)),
                Job.run_after <= now,
            )
            .order_by(Job.priority.desc(), Job.created_at, Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = (await self.db.execute(stmt)).scalar_one_or_none()
        if job is None:
            await self.db.commit()  # cierra la transacción sin expirar el estado del ORM
            return None
        job.status = JobStatus.PROCESSING.value
        job.attempts += 1
        job.lease_owner_id = worker_id
        job.lease_expires_at = now + timedelta(seconds=self.settings.job_lease_seconds)
        job.started_at = job.started_at or now
        job.progress = 0.0
        job.progress_message = None
        self._event(
            job,
            "claimed",
            f"Asignado a {worker_name} (intento {job.attempts}/{job.max_attempts})",
            {"worker_id": str(worker_id), "worker": worker_name},
        )
        await self.db.commit()
        return job

    async def _claimed(self, job: Job) -> ClaimedJob:
        if job.lease_expires_at is None:  # pragma: no cover - invariante de _try_claim
            raise RuntimeError("trabajo sin lease")
        return ClaimedJob(
            id=job.id,
            type=job.type,
            queue=job.queue,
            attempt=job.attempts,
            max_attempts=job.max_attempts,
            payload=job.payload,
            inputs=await self._inputs(job),
            lease_seconds=self.settings.job_lease_seconds,
            lease_expires_at=job.lease_expires_at,
            timeout_s=job.timeout_s,
        )

    async def _inputs(self, job: Job) -> list[JobInput]:
        """Entradas firmadas del trabajo (`payload.inputs`), fijadas por la API al crearlo."""
        refs = [InputRef.model_validate(r) for r in job.payload.get("inputs") or []]
        if not refs:
            return []
        objects = {
            o.id: o
            for o in (
                await self.db.execute(
                    select(StoredObject).where(StoredObject.id.in_([r.object_id for r in refs]))
                )
            ).scalars()
        }
        inputs: list[JobInput] = []
        for ref in refs:
            obj = objects.get(ref.object_id)
            if obj is None or obj.status != "available":
                raise Conflict(
                    f"La entrada '{ref.name}' ya no está disponible", code="input_unavailable"
                )
            signed = self.app.storage.presign_get(
                obj.key,
                audience=Audience.WORKER,
                ttl_seconds=self.settings.input_url_ttl_seconds,
            )
            inputs.append(
                JobInput(
                    name=ref.name,
                    object_id=obj.id,
                    url=signed.url,
                    content_type=obj.content_type,
                    size_bytes=obj.size_bytes,
                    sha256=obj.sha256,
                    expires_at=signed.expires_at,
                    kind=ref.kind,
                    extension=ref.extension,
                    key=ref.key,
                    width=ref.width,
                    height=ref.height,
                    duration_s=ref.duration_s,
                    has_audio=ref.has_audio,
                )
            )
        return inputs

    async def _owned(self, job_id: uuid.UUID, worker: Worker) -> Job:
        job = await self._lock(job_id)
        if job.status != JobStatus.PROCESSING.value or job.lease_owner_id != worker.id:
            raise Conflict("El worker ya no tiene asignado este trabajo", code="lease_lost")
        return job

    async def progress(self, job_id: uuid.UUID, worker: Worker, report: ProgressReport) -> LeaseAck:
        job = await self._owned(job_id, worker)
        now = _now()
        job.progress = report.progress
        if report.message and report.message != job.progress_message:
            self._event(job, "progress", report.message, {"progress": report.progress})
        job.progress_message = report.message
        lease = now + timedelta(seconds=self.settings.job_lease_seconds)
        job.lease_expires_at = lease
        worker.last_seen_at = now
        cancel = job.cancel_requested
        await self.db.commit()
        return LeaseAck(cancel_requested=cancel, lease_expires_at=lease)

    async def request_output(
        self, job_id: uuid.UUID, worker: Worker, req: OutputUploadRequest
    ) -> OutputUploadTicket:
        job = await self._owned(job_id, worker)
        spec = self._spec(job.type)
        expected = spec.outputs.get(req.name)
        if expected is None:
            raise ApiError(
                f"Salida '{req.name}' no prevista para {job.type}",
                code="unexpected_output",
                status_code=422,
            )
        if req.content_type != expected.content_type or req.content_type not in (
            OUTPUT_CONTENT_TYPES
        ):
            raise ApiError(
                f"Tipo de contenido no permitido para '{req.name}'",
                code="unsupported_content_type",
                status_code=422,
            )
        if req.size_bytes > self.settings.max_output_bytes:
            raise ApiError(
                "La salida supera el tamaño máximo permitido",
                code="output_too_large",
                status_code=413,
            )
        kind, extension = OUTPUT_CONTENT_TYPES[req.content_type]
        storage_kind = spec.storage_kind_for(spec.payload_model.model_validate(job.payload))
        existing = (
            await self.db.execute(
                select(JobOutput).where(
                    JobOutput.job_id == job.id,
                    JobOutput.attempt == job.attempts,
                    JobOutput.name == req.name,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            obj = existing.stored_object
            if obj.status != "pending":
                raise Conflict("La salida ya está registrada", code="output_exists")
        else:
            obj = StoredObject(
                bucket=self.app.storage.bucket,
                key=build_object_key(storage_kind, job.id, job.attempts, extension=extension),
                kind=storage_kind,
                status="pending",
                content_type=req.content_type,
                created_by_job_id=job.id,
            )
            self.db.add(obj)
            await self.db.flush()
            self.db.add(
                JobOutput(
                    job_id=job.id,
                    attempt=job.attempts,
                    name=req.name,
                    kind=kind.value,
                    object_id=obj.id,
                    verified=False,
                )
            )
            self._event(
                job,
                "output_registered",
                f"Salida '{req.name}' registrada",
                {"object_id": str(obj.id), "size_bytes": req.size_bytes},
            )
        await self.db.commit()
        signed = self.app.storage.presign_put(
            obj.key,
            audience=Audience.WORKER,
            ttl_seconds=self.settings.upload_url_ttl_seconds,
            content_type=req.content_type,
        )
        return OutputUploadTicket(
            object_id=obj.id,
            upload_url=signed.url,
            headers=signed.headers,
            expires_at=signed.expires_at,
        )

    async def complete(self, job_id: uuid.UUID, worker: Worker, req: CompleteRequest) -> Job:
        job = await self._owned(job_id, worker)
        now = _now()
        if job.cancel_requested:
            await self._finish(job, JobStatus.CANCELLED, now)
            self._event(job, "cancelled", "Cancelado (la salida se descarta)")
            await self.db.commit()
            return job
        if len(json.dumps(req.result).encode()) > MAX_RESULT_BYTES:
            raise ApiError("Resultado demasiado grande", code="result_too_large", status_code=413)

        spec = self._spec(job.type)
        outputs = {
            o.name: o
            for o in (
                await self.db.execute(
                    select(JobOutput).where(
                        JobOutput.job_id == job.id, JobOutput.attempt == job.attempts
                    )
                )
            ).scalars()
        }
        declared = {d.name: d for d in req.outputs}
        problems: dict[str, list[str]] = {}
        media_infos: dict[str, dict[str, Any]] = {}

        required = {n for n, o in spec.outputs.items() if o.required}
        for name in sorted(required - set(declared)):
            problems[name] = ["salida obligatoria no entregada"]

        payload = spec.payload_model.model_validate(job.payload)
        for name, decl in declared.items():
            out = outputs.get(name)
            if out is None or out.object_id != decl.object_id:
                problems[name] = ["salida no registrada para este intento"]
                continue
            issues, media_info = await self._verify_output(
                out.stored_object, decl.size_bytes, decl.sha256, spec, name, payload
            )
            if issues:
                problems[name] = issues
            if media_info is not None:
                media_infos[name] = media_info

        if problems:
            for name, out in outputs.items():
                out.verification = {"ok": False, "problems": problems.get(name, [])}
                if name in problems:
                    out.stored_object.status = "rejected"
            code = (
                ErrorCode.MISSING_OUTPUT
                if all(p == ["salida obligatoria no entregada"] for p in problems.values())
                else ErrorCode.OUTPUT_VERIFICATION_FAILED
            )
            job.error = {
                "code": code.value,
                "message": "La salida no supera la verificación del servidor",
                "retryable": False,
                "details": problems,
                "attempt": job.attempts,
            }
            await self._finish(job, JobStatus.FAILED, now)
            self._event(job, "verification_failed", "Verificación de salida fallida", problems)
            await self.db.commit()
            return job

        for name, out in outputs.items():
            if name not in declared:
                continue
            obj = out.stored_object
            obj.status = "available"
            obj.size_bytes = declared[name].size_bytes
            obj.sha256 = declared[name].sha256
            obj.verified_at = now
            obj.media_info = media_infos.get(name)
            out.verified = True
            out.verification = {"ok": True, "verified_at": now.isoformat()}
        job.result = {
            **req.result,
            "outputs": {name: str(declared[name].object_id) for name in declared},
        }
        job.progress = 1.0
        job.progress_message = "Completado y verificado"
        job.error = None
        await self._finish(job, JobStatus.COMPLETED, now)
        self._event(job, "completed", "Completado; salidas verificadas en servidor")
        await self.db.commit()
        return job

    async def _verify_output(
        self,
        obj: StoredObject,
        size_bytes: int,
        sha256: str,
        spec: JobTypeSpec,
        name: str,
        payload: Any,
    ) -> tuple[list[str], dict[str, Any] | None]:
        storage = self.app.storage
        try:
            head = await storage.head(obj.key)
        except StorageError as exc:
            return [f"error de almacenamiento: {exc}"], None
        if head is None:
            return ["el fichero no existe en el almacenamiento"], None
        if head.size_bytes != size_bytes:
            return [f"tamaño {head.size_bytes} distinto del declarado {size_bytes}"], None
        if head.size_bytes == 0:
            return ["fichero vacío"], None
        try:
            actual = await storage.sha256(obj.key)
        except StorageError as exc:
            return [f"error de almacenamiento: {exc}"], None
        if actual != sha256:
            return ["SHA-256 distinto del declarado (fichero corrupto o incompleto)"], None

        output_spec = spec.outputs[name]
        if output_spec.kind is OutputKind.JSON:
            if head.size_bytes > MAX_JSON_OUTPUT_BYTES:
                return ["JSON demasiado grande"], None
            try:
                parsed = json.loads(await storage.get_bytes(obj.key))
            except (ValueError, StorageError) as exc:
                return [f"JSON no válido: {exc}"], None
            if not isinstance(parsed, dict):
                return ["el JSON debe ser un objeto"], None
            return [], None
        if output_spec.kind not in (OutputKind.VIDEO, OutputKind.IMAGE):
            return [], None
        url = storage.presign_get(obj.key, audience=Audience.INTERNAL, ttl_seconds=300).url
        try:
            summary = await probe_url(
                self.settings.ffprobe_path,
                url,
                timeout_s=self.settings.ffprobe_timeout_seconds,
            )
        except (ProbeError, OSError) as exc:
            return [f"ffprobe no puede leer el fichero: {exc}"], None
        if output_spec.kind is OutputKind.IMAGE:
            image_issues = check_image_spec(summary, output_spec.image_spec or ImageSpec())
            return image_issues, summary.model_dump(mode="json")
        if output_spec.video_spec is None:
            return [], summary.model_dump(mode="json")
        issues = check_video_spec(summary, output_spec.video_spec(payload))
        return issues, summary.model_dump(mode="json")

    async def fail(self, job_id: uuid.UUID, worker: Worker, req: FailRequest) -> Job:
        job = await self._owned(job_id, worker)
        now = _now()
        if job.cancel_requested:
            await self._finish(job, JobStatus.CANCELLED, now)
            self._event(job, "cancelled", "Cancelado durante la ejecución")
            await self.db.commit()
            return job
        error: dict[str, Any] = {
            "code": req.code,
            "message": req.message,
            "retryable": req.retryable,
            "details": req.details,
            "attempt": job.attempts,
        }
        if req.retryable and job.attempts < job.max_attempts:
            self._schedule_retry(job, error, now)
            await self.db.commit()
            await self._wake(job.queue)
        else:
            job.error = error
            await self._finish(job, JobStatus.FAILED, now)
            self._event(job, "failed", req.message, {"code": req.code})
            await self.db.commit()
        return job

    async def ack_cancel(self, job_id: uuid.UUID, worker: Worker) -> Job:
        job = await self._owned(job_id, worker)
        if not job.cancel_requested:
            raise Conflict("No se ha solicitado cancelar este trabajo", code="not_cancelling")
        await self._finish(job, JobStatus.CANCELLED, _now())
        self._event(job, "cancelled", "Cancelación confirmada por el worker")
        await self.db.commit()
        return job

    async def reap_expired(self, *, limit: int = 100) -> int:
        """Devuelve a la cola (o da por fallidos) los trabajos cuyo lease ha expirado."""
        now = _now()
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.PROCESSING.value, Job.lease_expires_at < now)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list((await self.db.execute(stmt)).scalars())
        queues: set[str] = set()
        for job in jobs:
            error: dict[str, Any] = {
                "code": ErrorCode.LEASE_EXPIRED.value,
                "message": "El worker dejó de informar (lease expirado)",
                "retryable": True,
                "details": {"lease_owner_id": str(job.lease_owner_id)},
                "attempt": job.attempts,
            }
            if job.cancel_requested:
                await self._finish(job, JobStatus.CANCELLED, now)
                self._event(job, "cancelled", "Cancelado (worker sin respuesta)")
            elif job.attempts < job.max_attempts:
                self._event(job, "lease_expired", error["message"])
                self._schedule_retry(job, error, now)
                queues.add(job.queue)
            else:
                job.error = {**error, "retryable": False}
                await self._finish(job, JobStatus.FAILED, now)
                self._event(job, "failed", "Lease expirado y reintentos agotados")
        await self.db.commit()
        if queues:
            await self._wake(*queues)
        return len(jobs)


def is_terminal(status: str) -> bool:
    return JobStatus(status) in TERMINAL_STATUSES
