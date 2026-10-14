"""Bucle del worker: heartbeat → claim (long-poll) → ejecutar handler → completar/fallar.

Cada trabajo se ejecuta en un directorio temporal propio (0700) que se borra siempre al
terminar. Un hilo mantiene vivo el lease mientras el handler trabaja.
"""

from __future__ import annotations

import contextlib
import logging
import platform
import shutil
import socket
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from deken_shared.jobs import (
    ClaimedJob,
    ClaimRequest,
    CompleteRequest,
    ErrorCode,
    FailRequest,
    JobInput,
    OutputDeclaration,
    OutputUploadRequest,
    ProgressReport,
    Queue,
    WorkerHeartbeat,
)
from deken_worker import __version__
from deken_worker.capabilities import detect
from deken_worker.client import ApiClientError, LeaseLostError, WorkerClient
from deken_worker.config import WorkerSettings
from deken_worker.process import (
    ProcessCancelledError,
    ProcessFailedError,
    ProcessTimeoutError,
    UnsafePathError,
    ensure_within,
    sha256_file,
)

log = logging.getLogger("deken_worker")

HANDLER_ENTRY_POINT_GROUP = "deken_worker.handlers"
ENGINE_ENTRY_POINT_GROUP = "deken_worker.engines"


class JobError(Exception):
    """Fallo controlado de un handler, con código del contrato."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details


class JobCancelledError(Exception):
    pass


@dataclass
class HandlerResult:
    outputs: list[OutputDeclaration]
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobContext:
    job: ClaimedJob
    work_dir: Path
    settings: WorkerSettings
    client: WorkerClient
    cancel_event: threading.Event = field(default_factory=threading.Event)
    lease_lost: threading.Event = field(default_factory=threading.Event)
    deadline: float = 0.0
    _last_sent: float = 0.0
    _progress: float = 0.0
    _message: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def path(self, name: str) -> Path:
        """Ruta dentro del directorio aislado del trabajo."""
        return ensure_within(self.work_dir, Path(name))

    @property
    def remaining_s(self) -> float:
        return max(1.0, self.deadline - time.monotonic())

    def check_cancelled(self) -> None:
        if self.lease_lost.is_set():
            raise LeaseLostError(409, "lease_lost", "lease perdido")
        if self.cancel_event.is_set():
            raise JobCancelledError

    def report(self, progress: float, message: str | None = None, *, force: bool = False) -> None:
        with self._lock:
            self._progress = max(0.0, min(1.0, progress))
            if message is not None:
                self._message = message
            now = time.monotonic()
            due = now - self._last_sent >= self.settings.progress_min_interval_seconds
            if not (force or due or message is not None):
                return
            self._last_sent = now
            report = ProgressReport(progress=self._progress, message=self._message)
        try:
            ack = self.client.progress(self.job.id, report)
        except LeaseLostError:
            self.lease_lost.set()
            self.cancel_event.set()
            return
        except ApiClientError as exc:
            log.warning("No se pudo informar el progreso: %s", exc)
            return
        if ack.cancel_requested:
            self.cancel_event.set()

    def keepalive(self) -> None:
        self.report(self._progress, force=True)

    def download_input(self, item: JobInput, *, verify_sha256: bool = True) -> Path:
        """Descarga una entrada firmada al directorio aislado del trabajo."""
        ext = item.extension or "bin"
        target = ensure_within(self.work_dir, Path(f"{item.name}.{ext}"))
        self.check_cancelled()
        try:
            self.client.download(item.url, target)
        except ApiClientError as exc:
            raise JobError(ErrorCode.INPUT_UNAVAILABLE, str(exc), retryable=True) from exc
        if item.size_bytes is not None and target.stat().st_size != item.size_bytes:
            raise JobError(
                ErrorCode.INPUT_UNAVAILABLE,
                f"Tamaño de la entrada '{item.name}' distinto del esperado",
                retryable=True,
            )
        if verify_sha256 and item.sha256 and sha256_file(target) != item.sha256:
            raise JobError(
                ErrorCode.INPUT_UNAVAILABLE,
                f"SHA-256 de la entrada '{item.name}' distinto del registrado",
                retryable=True,
            )
        return target

    def upload_output(self, name: str, path: Path, content_type: str) -> OutputDeclaration:
        path = ensure_within(self.work_dir, path)
        self.check_cancelled()
        size = path.stat().st_size
        digest = sha256_file(path)
        ticket = self.client.request_output(
            self.job.id, OutputUploadRequest(name=name, content_type=content_type, size_bytes=size)
        )
        try:
            self.client.upload(ticket, path)
        except ApiClientError as exc:
            raise JobError(ErrorCode.UPLOAD_FAILED, str(exc), retryable=True) from exc
        return OutputDeclaration(
            name=name, object_id=ticket.object_id, sha256=digest, size_bytes=size
        )


Handler = Callable[[JobContext], HandlerResult]


def load_engines() -> dict[str, str]:
    """Información de motores (p. ej. Remotion) que declaran los paquetes de handlers."""
    engines: dict[str, str] = {}
    for ep in entry_points(group=ENGINE_ENTRY_POINT_GROUP):
        describe: Callable[[], Mapping[str, str]] = ep.load()
        engines.update(describe())
    return engines


def load_handlers() -> dict[str, Handler]:
    handlers: dict[str, Handler] = {}
    for ep in entry_points(group=HANDLER_ENTRY_POINT_GROUP):
        registered: Mapping[str, Handler] = ep.load()
        handlers.update(registered)
    return handlers


class Worker:
    def __init__(
        self,
        settings: WorkerSettings,
        client: WorkerClient,
        handlers: Mapping[str, Handler],
    ) -> None:
        self.settings = settings
        self.client = client
        self.handlers = dict(handlers)
        self.stop_event = threading.Event()
        self._last_heartbeat = 0.0
        settings.work_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    def heartbeat(self) -> None:
        caps = detect(self.settings.ffmpeg_path, self.settings.ffprobe_path, list(self.handlers))
        caps = caps.model_copy(update={"engines": load_engines()})
        ack = self.client.heartbeat(
            WorkerHeartbeat(
                hostname=socket.gethostname()[:255],
                platform=platform.platform()[:255],
                version=__version__,
                capabilities=caps,
            )
        )
        self._last_heartbeat = time.monotonic()
        log.info("Heartbeat OK como '%s' (colas: %s)", ack.name, ", ".join(ack.queues))

    def run_forever(self) -> None:
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                self.run_once()
                backoff = 1.0
            except ApiClientError as exc:
                if exc.status in {401, 403}:
                    log.error("La API rechaza el token del worker: %s", exc.message)
                    raise
                log.warning("Error de API: %s (reintento en %.0fs)", exc, backoff)
                self.stop_event.wait(backoff)
                backoff = min(60.0, backoff * 2)
            except OSError as exc:  # red caída: reintenta sin morir
                log.warning("Sin conexión con la API: %s (reintento en %.0fs)", exc, backoff)
                self.stop_event.wait(backoff)
                backoff = min(60.0, backoff * 2)

    def run_once(self, wait_seconds: int | None = None) -> bool:
        """Reclama y ejecuta como mucho un trabajo. Devuelve True si ejecutó uno."""
        if time.monotonic() - self._last_heartbeat >= self.settings.heartbeat_seconds:
            self.heartbeat()
        queues = [Queue(q) for q in self.settings.worker_queues]
        job = self.client.claim(
            ClaimRequest(
                queues=queues,
                job_types=sorted(self.handlers),
                wait_seconds=self.settings.claim_wait_seconds
                if wait_seconds is None
                else wait_seconds,
            )
        )
        if job is None:
            return False
        self.execute(job)
        return True

    def execute(self, job: ClaimedJob) -> None:
        log.info("Trabajo %s (%s) intento %d/%d", job.id, job.type, job.attempt, job.max_attempts)
        work_dir = Path(tempfile.mkdtemp(prefix=f"job-{job.id}-", dir=self.settings.work_dir))
        ctx = JobContext(
            job=job,
            work_dir=work_dir,
            settings=self.settings,
            client=self.client,
            deadline=time.monotonic() + job.timeout_s,
        )
        stop_keepalive = threading.Event()
        keepalive = threading.Thread(
            target=self._keepalive, args=(ctx, stop_keepalive), daemon=True
        )
        keepalive.start()
        try:
            self._run_handler(ctx)
        finally:
            stop_keepalive.set()
            keepalive.join(timeout=5)
            shutil.rmtree(work_dir, ignore_errors=True)

    def _keepalive(self, ctx: JobContext, stop: threading.Event) -> None:
        interval = max(2.0, ctx.job.lease_seconds / 3)
        while not stop.wait(interval):
            ctx.keepalive()

    def _fail(self, job: ClaimedJob, error: JobError) -> None:
        log.warning("Trabajo %s fallido: %s %s", job.id, error.code, error.message)
        try:
            self.client.fail(
                job.id,
                FailRequest(
                    code=error.code,
                    message=error.message[:2000],
                    retryable=error.retryable,
                    details=error.details,
                ),
            )
        except LeaseLostError:
            log.warning("Trabajo %s: lease perdido al informar el fallo", job.id)

    def _run_handler(self, ctx: JobContext) -> None:
        job = ctx.job
        handler = self.handlers.get(job.type)
        if handler is None:
            self._fail(
                job, JobError(ErrorCode.UNSUPPORTED_JOB_TYPE, f"Sin handler para {job.type}")
            )
            return
        try:
            ctx.report(0.0, "Iniciado", force=True)
            ctx.check_cancelled()
            result = handler(ctx)
            ctx.check_cancelled()
            ack = self.client.complete(
                job.id, CompleteRequest(outputs=result.outputs, result=result.result)
            )
            log.info("Trabajo %s → %s", job.id, ack.status.value)
        except (JobCancelledError, ProcessCancelledError):
            if ctx.lease_lost.is_set():
                log.warning("Trabajo %s abandonado: lease perdido", job.id)
                return
            log.info("Trabajo %s cancelado", job.id)
            with contextlib.suppress(LeaseLostError):
                self.client.ack_cancel(job.id)
        except LeaseLostError:
            log.warning("Trabajo %s abandonado: la API ya no lo asigna a este worker", job.id)
        except JobError as exc:
            self._fail(job, exc)
        except ValidationError as exc:
            self._fail(job, JobError(ErrorCode.INVALID_PAYLOAD, f"Payload no válido: {exc}"))
        except ProcessTimeoutError as exc:
            self._fail(job, JobError(ErrorCode.TIMEOUT, str(exc), retryable=True))
        except ProcessFailedError as exc:
            self._fail(job, JobError(ErrorCode.FFMPEG_FAILED, str(exc), retryable=True))
        except UnsafePathError as exc:
            self._fail(job, JobError(ErrorCode.WORKER_ERROR, str(exc)))
        except ApiClientError as exc:
            self._fail(job, JobError(ErrorCode.WORKER_ERROR, str(exc), retryable=True))
        except Exception as exc:
            log.exception("Error inesperado en el trabajo %s", job.id)
            self._fail(
                job,
                JobError(ErrorCode.WORKER_ERROR, f"{type(exc).__name__}: {exc}", retryable=True),
            )
