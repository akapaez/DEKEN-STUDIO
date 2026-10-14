"""Ejecución segura de FFmpeg/ffprobe.

Reglas:
- Siempre lista de argumentos; nunca `shell=True`.
- Solo ficheros dentro del directorio aislado del trabajo (`ensure_within`).
- Las entradas de fichero se abren con `-protocol_whitelist file` (sin red, sin
  `concat:`/`subfile:` ni otros protocolos que permitan leer rutas arbitrarias).
- Timeout y cancelación cooperativa: el proceso se mata si se superan.
"""

from __future__ import annotations

import hashlib
import json
import queue
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path

from deken_shared.media import ProbeSummary, parse_ffprobe_json


class ProcessError(RuntimeError):
    pass


class ProcessFailedError(ProcessError):
    def __init__(self, returncode: int, stderr_tail: str) -> None:
        super().__init__(f"código {returncode}: {stderr_tail}")
        self.returncode = returncode
        self.stderr_tail = stderr_tail


class ProcessTimeoutError(ProcessError):
    pass


class ProcessCancelledError(ProcessError):
    pass


class UnsafePathError(ValueError):
    pass


def ensure_within(base: Path, candidate: Path) -> Path:
    """Devuelve la ruta resuelta si está dentro de `base`; si no, lanza UnsafePathError."""
    base_r = base.resolve()
    resolved = (
        (base_r / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    )
    if resolved != base_r and not resolved.is_relative_to(base_r):
        raise UnsafePathError(f"ruta fuera del directorio de trabajo: {candidate}")
    return resolved


def file_input(path: Path) -> list[str]:
    """Argumentos para abrir un fichero local como entrada, sin otros protocolos."""
    return ["-protocol_whitelist", "file", "-i", str(path)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _pump(stream: object, sink: queue.Queue[str | None]) -> None:
    try:
        for line in stream:  # type: ignore[attr-defined]
            sink.put(line)
    finally:
        sink.put(None)


def run_ffmpeg(
    ffmpeg: str,
    args: list[str],
    *,
    cwd: Path,
    timeout_s: float,
    cancel: threading.Event | None = None,
    duration_s: float | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> str:
    """Ejecuta FFmpeg informando del progreso (0..1) a partir de `-progress`.

    Devuelve los mensajes de error emitidos (vacío si no hubo ninguno)."""
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-y",
        *args,
    ]
    proc = subprocess.Popen(  # noqa: S603 - lista de argumentos, sin shell
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out_q: queue.Queue[str | None] = queue.Queue()
    stderr_tail: deque[str] = deque(maxlen=40)
    t_out = threading.Thread(target=_pump, args=(proc.stdout, out_q), daemon=True)

    def _collect_stderr() -> None:
        for line in proc.stderr or []:
            stderr_tail.append(line.rstrip())

    t_err = threading.Thread(target=_collect_stderr, daemon=True)
    t_out.start()
    t_err.start()
    deadline = time.monotonic() + timeout_s
    stdout_open = True
    try:
        while True:
            if cancel is not None and cancel.is_set():
                raise ProcessCancelledError("cancelado")
            if time.monotonic() > deadline:
                raise ProcessTimeoutError(f"FFmpeg superó {timeout_s:.0f}s")
            if not stdout_open:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
            try:
                line = out_q.get(timeout=0.25)
            except queue.Empty:
                continue
            if line is None:
                stdout_open = False
                continue
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and duration_s and on_progress and value.isdigit():
                on_progress(min(1.0, int(value) / (duration_s * 1_000_000)))
    except BaseException:
        proc.kill()
        proc.wait(timeout=10)
        raise
    proc.wait(timeout=10)
    t_err.join(timeout=2)
    tail = "\n".join(stderr_tail)[-2000:]
    if proc.returncode != 0:
        raise ProcessFailedError(proc.returncode, tail)
    return tail


def probe_file(ffprobe: str, path: Path, *, timeout_s: float = 60) -> ProbeSummary:
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-protocol_whitelist",
        "file",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    try:
        done = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
            cmd, capture_output=True, timeout=timeout_s, check=False, stdin=subprocess.DEVNULL
        )
    except subprocess.TimeoutExpired as exc:
        raise ProcessTimeoutError("ffprobe superó el tiempo límite") from exc
    if done.returncode != 0:
        raise ProcessFailedError(done.returncode, done.stderr.decode(errors="replace")[-2000:])
    return parse_ffprobe_json(json.loads(done.stdout))


def verify_decodes(
    ffmpeg: str, path: Path, *, cwd: Path, timeout_s: float, cancel: threading.Event | None = None
) -> None:
    """Decodifica el fichero completo; cualquier error de decodificación lo invalida."""
    errors = run_ffmpeg(
        ffmpeg,
        ["-err_detect", "explode", "-xerror", *file_input(path), "-f", "null", "-"],
        cwd=cwd,
        timeout_s=timeout_s,
        cancel=cancel,
    )
    if errors.strip():
        raise ProcessFailedError(0, f"errores de decodificación: {errors}")


def run_json_lines(
    cmd: list[str],
    *,
    cwd: Path,
    timeout_s: float,
    cancel: threading.Event | None = None,
    on_event: Callable[[dict[str, object]], None] | None = None,
    env: dict[str, str] | None = None,
    grace_s: float = 15.0,
) -> tuple[int, list[dict[str, object]], str]:
    """Ejecuta un proceso que informa con una línea JSON por evento en stdout.

    En cancelación envía SIGTERM (el proceso puede limpiar y confirmar) y, si no termina
    en `grace_s`, lo mata. Devuelve (código, eventos, cola de stderr)."""
    proc = subprocess.Popen(  # noqa: S603 - lista de argumentos, sin shell
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out_q: queue.Queue[str | None] = queue.Queue()
    stderr_tail: deque[str] = deque(maxlen=60)

    def _collect_stderr() -> None:
        for line in proc.stderr or []:
            stderr_tail.append(line.rstrip())

    threading.Thread(target=_pump, args=(proc.stdout, out_q), daemon=True).start()
    t_err = threading.Thread(target=_collect_stderr, daemon=True)
    t_err.start()
    events: list[dict[str, object]] = []
    deadline = time.monotonic() + timeout_s
    terminating_since: float | None = None
    stdout_open = True
    timed_out = False
    try:
        while True:
            now = time.monotonic()
            if terminating_since is None and (
                (cancel is not None and cancel.is_set()) or now > deadline
            ):
                timed_out = now > deadline
                proc.terminate()
                terminating_since = now
            if terminating_since is not None and now - terminating_since > grace_s:
                proc.kill()
            if not stdout_open:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
            try:
                line = out_q.get(timeout=0.25)
            except queue.Empty:
                continue
            if line is None:
                stdout_open = False
                continue
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
                if on_event is not None:
                    on_event(event)
    except BaseException:
        proc.kill()
        proc.wait(timeout=10)
        raise
    proc.wait(timeout=30)
    t_err.join(timeout=2)
    tail = "\n".join(stderr_tail)[-3000:]
    if terminating_since is not None:
        if timed_out:
            raise ProcessTimeoutError(f"El proceso superó {timeout_s:.0f}s")
        raise ProcessCancelledError("cancelado")
    return proc.returncode or 0, events, tail
