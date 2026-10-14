"""Operaciones FFmpeg de la ingesta. Todas sobre ficheros del directorio del trabajo.

FFmpeg aplica la rotación del móvil al decodificar (autorotate), por eso los filtros
trabajan con las dimensiones de visualización. Nunca se deforma: escalado proporcional
y `setsar=1` (píxel cuadrado).
"""

from __future__ import annotations

import array
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from deken_worker.process import (
    ProcessCancelledError,
    ProcessFailedError,
    ProcessTimeoutError,
    file_input,
    run_ffmpeg,
)

PCM_RATE = 8000


def poster_args(source: Path, out: str, *, at_s: float, max_px: int) -> list[str]:
    scale = (
        f"scale='if(gte(iw,ih),min({max_px},iw),-1)':'if(gte(iw,ih),-1,min({max_px},ih))'"
        ":flags=lanczos,setsar=1"
    )
    return [
        "-ss",
        f"{at_s:.3f}",
        *file_input(source),
        "-frames:v",
        "1",
        "-vf",
        scale,
        "-q:v",
        "3",
        out,
    ]


def strip_args(source: Path, out: str, *, frames: int, duration_s: float, height: int) -> list[str]:
    rate = f"{frames}/{max(duration_s, 0.1):.3f}"
    vf = f"fps={rate},scale=-1:{height}:flags=lanczos,setsar=1,tile={frames}x1"
    return [*file_input(source), "-an", "-vf", vf, "-frames:v", "1", "-q:v", "4", out]


def proxy_args(
    source: Path, out: str, *, width: int, height: int, fps: float, has_audio: bool
) -> list[str]:
    vf = f"scale={width}:{height}:flags=bicubic,setsar=1,fps={fps:g}"
    audio = (
        ["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]
        if has_audio
        else ["-an"]
    )
    return [
        *file_input(source),
        "-map", "0:v:0", *audio,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-g", str(max(1, round(fps * 2))),
        "-movflags", "+faststart",
        "-metadata", "comment=DEKEN STUDIO AI - proxy de previsualización (no es el original)",
        out,
    ]  # fmt: skip


def decode_sample(
    ffmpeg: str,
    source: Path,
    *,
    cwd: Path,
    seconds: float,
    timeout_s: float,
    cancel: threading.Event | None,
) -> str:
    """Decodifica los primeros segundos del vídeo; devuelve los avisos emitidos."""
    return run_ffmpeg(
        ffmpeg,
        [
            "-xerror",
            "-t",
            f"{seconds:.3f}",
            *file_input(source),
            "-map",
            "0:v:0",
            "-f",
            "null",
            "-",
        ],
        cwd=cwd,
        timeout_s=timeout_s,
        cancel=cancel,
    )


def waveform_peaks(
    ffmpeg: str,
    source: Path,
    *,
    points: int,
    duration_s: float,
    timeout_s: float,
    cancel: threading.Event | None,
    on_progress: Callable[[float], None] | None = None,
) -> list[float]:
    """Picos normalizados (0–1) del audio, en `points` tramos, sin cargar todo en memoria."""
    cmd = [
        ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error",
        *file_input(source), "-map", "0:a:0", "-ac", "1", "-ar", str(PCM_RATE),
        "-f", "s16le", "-",
    ]  # fmt: skip
    expected = max(1, round(duration_s * PCM_RATE))
    per_bucket = max(1, expected // points)
    peaks = [0] * points
    proc = subprocess.Popen(  # noqa: S603 - lista de argumentos, sin shell
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    deadline = time.monotonic() + timeout_s
    index = 0
    try:
        assert proc.stdout is not None  # noqa: S101 - PIPE garantizado
        while chunk := proc.stdout.read(64 * 1024):
            if cancel is not None and cancel.is_set():
                raise ProcessCancelledError("cancelado")
            if time.monotonic() > deadline:
                raise ProcessTimeoutError("La forma de onda superó el tiempo límite")
            samples = array.array("h")
            samples.frombytes(chunk[: len(chunk) - len(chunk) % 2])
            for value in samples:
                bucket = min(points - 1, index // per_bucket)
                magnitude = -value if value < 0 else value
                if magnitude > peaks[bucket]:
                    peaks[bucket] = magnitude
                index += 1
            if on_progress:
                on_progress(min(1.0, index / expected))
    except BaseException:
        proc.kill()
        proc.wait(timeout=10)
        raise
    stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
    if proc.wait(timeout=30) != 0:
        raise ProcessFailedError(proc.returncode, stderr[-2000:])
    used = min(points, max(1, -(-index // per_bucket)))
    # Nivel absoluto (no normalizado): permite ver silencios y niveles reales.
    return [round(p / 32768, 4) for p in peaks[:used]]
