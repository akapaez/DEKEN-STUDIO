"""Operaciones FFmpeg de la ingesta sobre señales SINTÉTICAS (barras y tono)."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

from deken_analysis.ffmpeg_ops import (
    decode_sample,
    poster_args,
    proxy_args,
    strip_args,
    waveform_peaks,
)
from deken_worker.process import ProcessCancelledError, ProcessFailedError, probe_file, run_ffmpeg

pytestmark = pytest.mark.media


def _video(path: Path, size: str = "640x360", seconds: float = 2, audio: bool = True) -> Path:
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={size}:rate=30:duration={seconds}",
    ]
    if audio:
        cmd += [
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}:sample_rate=48000",
            "-c:a",
            "aac",
        ]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-metadata", "comment=SINTETICO", str(path)]
    subprocess.run(cmd, check=True, timeout=60)  # fmt: skip
    return path


def _size(path: Path) -> tuple[int, int]:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "json"]
    out = subprocess.run([*cmd, str(path)], capture_output=True, check=True)
    stream = json.loads(out.stdout)["streams"][0]
    return stream["width"], stream["height"]


def _run(tmp_path: Path, args: list[str]) -> None:
    run_ffmpeg("ffmpeg", args, cwd=tmp_path, timeout_s=60)


def test_poster_strip_and_proxy_keep_aspect(tmp_path: Path) -> None:
    source = _video(tmp_path / "in.mp4")
    _run(tmp_path, poster_args(source, "poster.jpg", at_s=0.5, max_px=320))
    assert _size(tmp_path / "poster.jpg") == (320, 180)
    _run(tmp_path, strip_args(source, "strip.jpg", frames=5, duration_s=2, height=90))
    assert _size(tmp_path / "strip.jpg") == (160 * 5, 90)
    _run(tmp_path, proxy_args(source, "proxy.mp4", width=320, height=180, fps=25, has_audio=True))
    assert _size(tmp_path / "proxy.mp4") == (320, 180)


def test_poster_never_upscales(tmp_path: Path) -> None:
    source = _video(tmp_path / "small.mp4", size="200x100", audio=False)
    _run(tmp_path, poster_args(source, "p.jpg", at_s=0, max_px=720))
    assert _size(tmp_path / "p.jpg") == (200, 100)


def test_waveform_peaks(tmp_path: Path) -> None:
    source = _video(tmp_path / "tone.mp4", seconds=2)
    progress: list[float] = []
    peaks = waveform_peaks(
        "ffmpeg", source, points=100, duration_s=2, timeout_s=30, cancel=None,
        on_progress=progress.append,
    )  # fmt: skip
    assert 95 <= len(peaks) <= 100
    assert all(0 <= p <= 1 for p in peaks)
    assert max(peaks) > 0.1  # tono audible, nivel absoluto (no normalizado)
    assert progress and progress[-1] > 0.9

    cancel = threading.Event()
    cancel.set()
    with pytest.raises(ProcessCancelledError):
        waveform_peaks("ffmpeg", source, points=10, duration_s=2, timeout_s=30, cancel=cancel)


def test_decode_sample_detects_corruption(tmp_path: Path) -> None:
    source = _video(tmp_path / "ok.mp4", seconds=2, audio=False)
    decode_sample("ffmpeg", source, cwd=tmp_path, seconds=2, timeout_s=30, cancel=None)
    data = bytearray(source.read_bytes())
    start = data.find(b"mdat") + 4  # cabeceras intactas, datos de vídeo aleatorios
    end = start + (len(data) - start) * 3 // 4
    data[start + 64 : end] = os.urandom(end - start - 64)
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(bytes(data))
    with pytest.raises(ProcessFailedError):
        decode_sample("ffmpeg", broken, cwd=tmp_path, seconds=2, timeout_s=30, cancel=None)


def _hlg_and_sdr(tmp_path: Path) -> tuple[Path, Path]:
    """Las mismas barras en SDR BT.709 y codificadas como HLG BT.2020 10 bits (tipo iPhone)."""
    bars = ["-f", "lavfi", "-i", "smptebars=size=640x360:rate=30:duration=1"]
    sdr = tmp_path / "sdr.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *bars, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(sdr)],
        check=True, timeout=60,
    )  # fmt: skip
    hlg = tmp_path / "hlg.mov"
    to_hlg = (
        "format=gbrpf32le,zscale=tin=bt709:t=arib-std-b67:pin=bt709:p=bt2020:min=bt709:"
        "m=bt2020nc:r=tv,format=yuv420p10le"
    )
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *bars, "-vf", to_hlg, "-c:v", "libx265",
         "-preset", "ultrafast", "-x265-params", "log-level=error", "-tag:v", "hvc1",
         "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
         "-metadata", "comment=SINTETICO", str(hlg)],
        check=True, timeout=120,
    )  # fmt: skip
    return hlg, sdr


def _psnr(a: Path, b: Path) -> float:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b), "-filter_complex",
         "[0:v][1:v]psnr", "-frames:v", "5", "-f", "null", "-"],
        capture_output=True, text=True, check=True, timeout=60,
    )  # fmt: skip
    return float(out.stderr.rsplit("average:", 1)[1].split()[0])


def test_hdr_proxy_is_tone_mapped_to_sdr(tmp_path: Path) -> None:
    hlg, sdr = _hlg_and_sdr(tmp_path)
    probe = probe_file("ffprobe", hlg, timeout_s=30)
    assert probe.video_streams[0].dynamic_range == "hlg"

    def proxy(src: Path, name: str, hdr: bool) -> Path:
        _run(
            tmp_path, proxy_args(src, name, width=640, height=360, fps=30, has_audio=False, hdr=hdr)
        )
        return tmp_path / name

    reference = proxy(sdr, "ref.mp4", hdr=False)
    washed = proxy(hlg, "sin-mapeo.mp4", hdr=False)
    mapped = proxy(hlg, "con-mapeo.mp4", hdr=True)
    # Sin mapeo de tono el proxy sale lavado; con él, cerca de la referencia SDR.
    assert _psnr(reference, washed) < 22
    assert _psnr(reference, mapped) > 24
    video = probe_file("ffprobe", mapped, timeout_s=30).video_streams[0]
    assert (video.color_transfer, video.color_primaries, video.pix_fmt) == (
        "bt709",
        "bt709",
        "yuv420p",
    )
    assert video.dynamic_range == "sdr"

    _run(tmp_path, poster_args(hlg, "p.jpg", at_s=0, max_px=320, hdr=True))
    # Tamaño proporcional impar (como un póster 405×720): no debe romper el mapeo de tono.
    _run(tmp_path, poster_args(hlg, "impar.jpg", at_s=0, max_px=225, hdr=True))
    assert _size(tmp_path / "impar.jpg") == (225, 127)
    _run(tmp_path, strip_args(hlg, "s.jpg", frames=3, duration_s=1, height=90, hdr=True))
    assert _size(tmp_path / "s.jpg") == (160 * 3, 90)
