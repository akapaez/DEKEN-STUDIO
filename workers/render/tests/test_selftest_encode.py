"""El autotest produce exactamente la especificación de exportación V1."""

from __future__ import annotations

from pathlib import Path

import pytest

from deken_render.selftest import SYNTHETIC_COMMENT, encode_args
from deken_shared.jobs import RenderSelftestPayload
from deken_shared.media import check_video_spec
from deken_worker.process import probe_file, run_ffmpeg, verify_decodes

pytestmark = pytest.mark.media


@pytest.mark.parametrize("duration", [1.0, 2.5])
def test_selftest_encoding_meets_spec(tmp_path: Path, duration: float) -> None:
    payload = RenderSelftestPayload(duration_s=duration)
    run_ffmpeg("ffmpeg", encode_args(payload, "out.mp4"), cwd=tmp_path, timeout_s=120)
    out = tmp_path / "out.mp4"
    summary = probe_file("ffprobe", out)
    assert check_video_spec(summary, payload.video_spec()) == []
    verify_decodes("ffmpeg", out, cwd=tmp_path, timeout_s=120)


def test_selftest_is_labelled_as_synthetic() -> None:
    args = encode_args(RenderSelftestPayload(), "out.mp4")
    assert f"comment={SYNTHETIC_COMMENT}" in args
    assert "title=AUTOTEST SINTÉTICO" in args
