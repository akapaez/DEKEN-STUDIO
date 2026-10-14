"""Ejecución segura de FFmpeg: rutas, progreso, cancelación, timeout y errores."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from deken_worker.capabilities import detect
from deken_worker.process import (
    ProcessCancelledError,
    ProcessFailedError,
    ProcessTimeoutError,
    UnsafePathError,
    ensure_within,
    file_input,
    probe_file,
    run_ffmpeg,
    sha256_file,
    verify_decodes,
)

pytestmark = pytest.mark.media

TESTSRC = ["-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration={d}"]


def _encode(tmp_path: Path, duration: float = 1.0, **kw: object) -> list[str]:
    return [*(a.format(d=duration) for a in TESTSRC), "-c:v", "libx264", "-preset",
            "ultrafast", "-pix_fmt", "yuv420p", "out.mp4"]  # fmt: skip


def test_ensure_within(tmp_path: Path) -> None:
    assert ensure_within(tmp_path, Path("a/b.mp4")) == (tmp_path / "a/b.mp4").resolve()
    for bad in ("../x", "/etc/passwd", "a/../../x"):
        with pytest.raises(UnsafePathError):
            ensure_within(tmp_path, Path(bad))
    outside = tmp_path.parent / "fuera"
    outside.mkdir(exist_ok=True)
    (tmp_path / "enlace").symlink_to(outside)
    with pytest.raises(UnsafePathError):
        ensure_within(tmp_path, Path("enlace/x.mp4"))


def test_file_input_restricts_protocols(tmp_path: Path) -> None:
    assert file_input(tmp_path / "x.mov")[:3] == ["-protocol_whitelist", "file", "-i"]


def test_run_ffmpeg_reports_progress_and_probes(tmp_path: Path) -> None:
    seen: list[float] = []
    run_ffmpeg("ffmpeg", _encode(tmp_path, 2.0), cwd=tmp_path, timeout_s=60,
               duration_s=2.0, on_progress=seen.append)  # fmt: skip
    out = tmp_path / "out.mp4"
    assert out.stat().st_size > 0
    assert seen and seen[-1] == pytest.approx(1.0, abs=0.1)
    summary = probe_file("ffprobe", out)
    assert summary.video_streams[0].width == 320
    verify_decodes("ffmpeg", out, cwd=tmp_path, timeout_s=60)
    assert len(sha256_file(out)) == 64


def test_run_ffmpeg_failure_has_stderr(tmp_path: Path) -> None:
    with pytest.raises(ProcessFailedError) as exc:
        run_ffmpeg("ffmpeg", [*file_input(tmp_path / "no-existe.mp4"), "out.mp4"],
                   cwd=tmp_path, timeout_s=30)  # fmt: skip
    assert "no-existe" in exc.value.stderr_tail


def test_protocol_whitelist_blocks_other_protocols(tmp_path: Path) -> None:
    with pytest.raises(ProcessFailedError):
        run_ffmpeg("ffmpeg", ["-protocol_whitelist", "file", "-i", "concat:/etc/passwd",
                              "out.mp4"], cwd=tmp_path, timeout_s=30)  # fmt: skip


def test_run_ffmpeg_cancellation_kills_process(tmp_path: Path) -> None:
    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    started = time.monotonic()
    with pytest.raises(ProcessCancelledError):
        run_ffmpeg("ffmpeg", _encode(tmp_path, 600.0), cwd=tmp_path, timeout_s=60,
                   cancel=cancel)  # fmt: skip
    assert time.monotonic() - started < 10


def test_run_ffmpeg_timeout(tmp_path: Path) -> None:
    with pytest.raises(ProcessTimeoutError):
        run_ffmpeg("ffmpeg", _encode(tmp_path, 600.0), cwd=tmp_path, timeout_s=0.5)


def test_verify_decodes_rejects_corrupt_file(tmp_path: Path) -> None:
    run_ffmpeg("ffmpeg", _encode(tmp_path, 2.0), cwd=tmp_path, timeout_s=60)
    out = tmp_path / "out.mp4"
    data = bytearray(out.read_bytes())
    mid = len(data) // 2
    data[mid : mid + 4000] = b"\x00" * 4000
    out.write_bytes(bytes(data))
    with pytest.raises(ProcessFailedError):
        verify_decodes("ffmpeg", out, cwd=tmp_path, timeout_s=60)


def test_capabilities_detection() -> None:
    caps = detect("ffmpeg", "ffprobe", ["system.render_selftest"])
    assert caps.ffmpeg_version and caps.ffprobe_version
    assert "libx264" in caps.encoders and "aac" in caps.encoders
    assert caps.job_types == ["system.render_selftest"]
    missing = detect("/nonexistent/ffmpeg", "/nonexistent/ffprobe", [])
    assert missing.ffmpeg_version is None and missing.encoders == []
