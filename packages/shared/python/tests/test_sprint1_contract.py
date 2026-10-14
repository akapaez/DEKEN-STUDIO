"""Contrato Sprint 1: nuevos tipos de trabajo, rotación de móvil, imágenes y timeline."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from deken_shared.jobs import (
    JobType,
    MediaIngestPayload,
    ProxyTarget,
    RemotionEvalPayload,
    RenderTimelinePayload,
    get_job_type_spec,
)
from deken_shared.media import (
    ImageSpec,
    ProbeSummary,
    StreamSummary,
    VideoSpec,
    _rotation,
    check_image_spec,
    check_video_spec,
    parse_ffprobe_json,
    parse_ratio,
)


def test_parse_ratio() -> None:
    assert parse_ratio("16:9") == pytest.approx(16 / 9)
    assert parse_ratio("0:1") is None
    assert parse_ratio("N/A") is None
    assert parse_ratio(None) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"side_data_list": [{"rotation": -90}]}, 270),
        ({"side_data_list": [{"rotation": 90}]}, 90),
        ({"tags": {"rotate": "180"}}, 180),
        ({"side_data_list": [{"rotation": 45}]}, None),
        ({}, None),
    ],
)
def test_rotation_from_display_matrix_or_tag(raw: dict[str, Any], expected: int | None) -> None:
    assert _rotation(raw) == expected


def test_display_size_applies_rotation_and_sar() -> None:
    portrait = StreamSummary(index=0, codec_type="video", width=1920, height=1080, rotation=90)
    assert portrait.display_size == (1080, 1920)
    anamorphic = StreamSummary(
        index=0, codec_type="video", width=1440, height=1080, sample_aspect_ratio="4:3"
    )
    assert anamorphic.display_size == (1920, 1080)
    assert StreamSummary(index=0, codec_type="audio").display_size is None


def test_ffprobe_parsing_keeps_rotation() -> None:
    summary = parse_ffprobe_json(
        {
            "format": {"format_name": "mov,mp4", "duration": "3.0"},
            "streams": [
                {
                    "index": 0,
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1280,
                    "height": 720,
                    "avg_frame_rate": "30000/1001",
                    "side_data_list": [{"side_data_type": "Display Matrix", "rotation": -90}],
                }
            ],
        }
    )
    video = summary.video_streams[0]
    assert video.rotation == 270
    assert video.display_size == (720, 1280)
    assert video.avg_frame_rate == pytest.approx(29.97, abs=0.01)


def _image(codec: str = "mjpeg", width: int = 405, height: int = 720) -> ProbeSummary:
    return ProbeSummary(
        format_name="image2",
        streams=[
            StreamSummary(index=0, codec_type="video", codec_name=codec, width=width, height=height)
        ],
    )


def test_check_image_spec() -> None:
    spec = ImageSpec(codecs=("mjpeg",), max_width=720, max_height=720)
    assert check_image_spec(_image(), spec) == []
    assert check_image_spec(_image(codec="png"), spec) == ["formato de imagen 'png' no admitido"]
    assert "demasiado grande" in check_image_spec(_image(width=1000), spec)[0]
    assert check_image_spec(ProbeSummary(format_name="x", streams=[]), spec)


def test_fractional_fps_spec() -> None:
    spec = VideoSpec(width=540, height=960, fps=29.97, duration_s=3.0, frame_tolerance=2)
    assert spec.expected_frames == 90
    summary = ProbeSummary(
        format_name="mov,mp4,m4a,3gp,3g2,mj2",
        duration_s=3.003,
        streams=[
            StreamSummary(index=0, codec_type="video", codec_name="h264", width=540, height=960,
                          pix_fmt="yuv420p", avg_frame_rate=30000 / 1001, nb_frames=90,
                          sample_aspect_ratio="1:1"),
            StreamSummary(index=1, codec_type="audio", codec_name="aac", sample_rate=48000),
        ],
    )  # fmt: skip
    assert check_video_spec(summary, spec) == []


def test_ingest_payload_proxy_spec_tolerances() -> None:
    payload = MediaIngestPayload(
        asset_id=uuid.uuid4(),
        inputs=[
            {"name": "original", "object_id": uuid.uuid4(), "kind": "video", "extension": "mov"},
        ],
        proxy=ProxyTarget(width=960, height=540, fps=25.0, duration_s=120.0, has_audio=False),
    )  # fmt: skip
    spec = payload.proxy_spec()
    assert (spec.width, spec.height, spec.fps, spec.audio_codec) == (960, 540, 25.0, None)
    assert spec.frame_tolerance == 30  # 1 % de 3000 fotogramas
    assert spec.container_tolerance_s == pytest.approx(1.2)
    with pytest.raises(ValidationError):
        MediaIngestPayload(asset_id=uuid.uuid4(), inputs=[], proxy=payload.proxy)


def test_storage_kind_depends_on_purpose() -> None:
    timeline_spec = get_job_type_spec(JobType.RENDER_TIMELINE.value)
    timeline = {"output": {"width": 1920, "height": 1080, "fps": 25, "duration_frames": 250}}
    evaluation = RenderTimelinePayload(timeline=timeline)
    production = RenderTimelinePayload(timeline=timeline, purpose="production")
    assert timeline_spec.storage_kind_for(evaluation) == "evaluation"
    assert timeline_spec.storage_kind_for(production) == "render"
    video = evaluation.video_spec()
    assert (video.width, video.height, video.fps, video.duration_s) == (1920, 1080, 25.0, 10.0)
    assert video.frame_tolerance == 0

    eval_spec = get_job_type_spec(JobType.SYSTEM_REMOTION_EVAL.value)
    assert eval_spec.storage_kind_for(RemotionEvalPayload()) == "evaluation"
    assert (
        get_job_type_spec(JobType.SYSTEM_RENDER_SELFTEST.value).storage_kind_for(None)
        == "system_test"
    )


def test_media_ingest_outputs() -> None:
    spec = get_job_type_spec(JobType.MEDIA_INGEST.value)
    assert spec.queue.value == "analysis"
    assert set(spec.outputs) == {"poster", "strip", "proxy", "waveform"}
    assert spec.outputs["waveform"].required is False  # vídeos sin audio
    assert all(spec.outputs[n].required for n in ("poster", "strip", "proxy"))
    assert spec.storage_kind_for(None) == "derived"


def test_remotion_eval_payload_is_the_fixed_technical_test() -> None:
    video = RemotionEvalPayload().video_spec()
    assert (video.width, video.height, video.fps, video.duration_s) == (1080, 1920, 30, 5)
    assert video.expected_frames == 150
    with pytest.raises(ValidationError):
        RemotionEvalPayload(title="x" * 41)
