"""Detección de capacidades del equipo (versiones de FFmpeg, codificadores, GPU)."""

from __future__ import annotations

import re
import subprocess

from deken_shared.jobs import WorkerCapabilities

INTERESTING_ENCODERS = (
    "libx264",
    "h264_nvenc",
    "h264_qsv",
    "h264_vaapi",
    "h264_amf",
    "hevc_nvenc",
    "aac",
    "libfdk_aac",
    "libmp3lame",
)


def _run(cmd: list[str]) -> str | None:
    try:
        done = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
            cmd, capture_output=True, timeout=15, check=False, stdin=subprocess.DEVNULL
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.decode(errors="replace")


def _version(binary: str, name: str) -> str | None:
    out = _run([binary, "-hide_banner", "-version"])
    if out is None:
        return None
    match = re.search(rf"{name} version (\S+)", out)
    return match.group(1) if match else None


def detect(ffmpeg: str, ffprobe: str, job_types: list[str]) -> WorkerCapabilities:
    encoders_out = _run([ffmpeg, "-hide_banner", "-encoders"]) or ""
    available = set(re.findall(r"^\s*[VAS][.A-Z]{5}\s+(\S+)", encoders_out, flags=re.MULTILINE))
    hwaccels_out = _run([ffmpeg, "-hide_banner", "-hwaccels"]) or ""
    hwaccels = [
        line.strip()
        for line in hwaccels_out.splitlines()[1:]
        if line.strip() and not line.startswith("Hardware")
    ]
    return WorkerCapabilities(
        ffmpeg_version=_version(ffmpeg, "ffmpeg"),
        ffprobe_version=_version(ffprobe, "ffprobe"),
        encoders=[e for e in INTERESTING_ENCODERS if e in available],
        hwaccels=hwaccels[:50],
        job_types=sorted(job_types),
        max_concurrency=1,
    )
