"""Unitarios del contrato compartido: verificación de vídeo y registro de tipos."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from deken_shared.jobs import (
    JOB_TYPES,
    OUTPUT_CONTENT_TYPES,
    ClaimRequest,
    FailRequest,
    JobType,
    OutputDeclaration,
    OutputKind,
    RenderSelftestPayload,
    get_job_type_spec,
    is_valid_output_name,
)
from deken_shared.media import VideoSpec, check_video_spec, parse_ffprobe_json, parse_rate


def _probe(**overrides: Any) -> dict[str, Any]:
    video = {
        "index": 0,
        "codec_type": "video",
        "codec_name": "h264",
        "width": 1080,
        "height": 1920,
        "pix_fmt": "yuv420p",
        "sample_aspect_ratio": "1:1",
        "avg_frame_rate": "30/1",
        "r_frame_rate": "30/1",
        "nb_frames": "90",
        "duration": "3.000000",
    }
    audio = {
        "index": 1,
        "codec_type": "audio",
        "codec_name": "aac",
        "sample_rate": "48000",
        "channels": 2,
        "duration": "3.000000",
    }
    video.update(overrides.pop("video", {}))
    audio.update(overrides.pop("audio", {}))
    streams = overrides.pop("streams", [video, audio])
    fmt = {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "3.000000", "size": "1000"}
    fmt.update(overrides.pop("format", {}))
    return {"format": fmt, "streams": streams}


SPEC = VideoSpec(duration_s=3.0)


def test_valid_probe_has_no_problems() -> None:
    assert check_video_spec(parse_ffprobe_json(_probe()), SPEC) == []


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"video": {"width": 1920, "height": 1080}}, "resolución 1920x1080"),
        ({"video": {"codec_name": "hevc"}}, "códec de vídeo"),
        ({"video": {"avg_frame_rate": "25/1"}}, "fps"),
        ({"video": {"nb_frames": "80"}}, "fotogramas"),
        ({"video": {"pix_fmt": "yuv444p"}}, "formato de píxel"),
        ({"video": {"sample_aspect_ratio": "4:3"}}, "deformada"),
        ({"audio": {"codec_name": "mp3"}}, "códec de audio"),
        ({"audio": {"sample_rate": "44100"}}, "frecuencia de audio"),
        ({"audio": {"duration": "2.5"}}, "desincronía"),
        ({"format": {"duration": "4.0"}}, "duración 4.000s"),
        ({"format": {"format_name": "matroska,webm"}}, "contenedor"),
    ],
)
def test_spec_violations_are_detected(overrides: dict[str, Any], fragment: str) -> None:
    problems = check_video_spec(parse_ffprobe_json(_probe(**overrides)), SPEC)
    assert any(fragment in p for p in problems), problems


def test_missing_audio_and_extra_video_are_detected() -> None:
    probe = _probe()
    only_video = _probe(streams=[probe["streams"][0]])
    assert any(
        "pista de audio" in p for p in check_video_spec(parse_ffprobe_json(only_video), SPEC)
    )
    twice = _probe(streams=[probe["streams"][0], probe["streams"][0], probe["streams"][1]])
    assert any("pista de vídeo" in p for p in check_video_spec(parse_ffprobe_json(twice), SPEC))


def test_parse_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="formato"):
        parse_ffprobe_json({"streams": []})
    assert parse_rate("30000/1001") == pytest.approx(29.97, rel=1e-3)
    assert parse_rate("0/0") is None
    assert parse_rate("abc") is None


def test_expected_frames() -> None:
    assert VideoSpec(duration_s=2.0, fps=30).expected_frames == 60
    assert VideoSpec(duration_s=1.5, fps=25).expected_frames == 38


def test_registry_is_consistent() -> None:
    for job_type, spec in JOB_TYPES.items():
        assert spec.job_type is job_type
        assert get_job_type_spec(job_type.value) is spec
        for name, output in spec.outputs.items():
            assert is_valid_output_name(name)
            assert OUTPUT_CONTENT_TYPES[output.content_type][0] is output.kind
    with pytest.raises(KeyError):
        get_job_type_spec("desconocido")


def test_selftest_payload_bounds_and_spec() -> None:
    payload = RenderSelftestPayload()
    spec = JOB_TYPES[JobType.SYSTEM_RENDER_SELFTEST].outputs["video"]
    assert spec.kind is OutputKind.VIDEO
    assert spec.video_spec is not None
    video_spec = spec.video_spec(payload)
    assert (video_spec.width, video_spec.height, video_spec.fps) == (1080, 1920, 30)
    with pytest.raises(ValidationError):
        RenderSelftestPayload(duration_s=0.1)
    with pytest.raises(ValidationError):
        RenderSelftestPayload.model_validate({"duration_s": 2, "extra": 1})


@pytest.mark.parametrize("name", ["video", "thumb_01", "a-b"])
def test_valid_output_names(name: str) -> None:
    assert is_valid_output_name(name)


@pytest.mark.parametrize("name", ["", "../x", "Video", "a/b", "x" * 65, "-x"])
def test_invalid_output_names(name: str) -> None:
    assert not is_valid_output_name(name)


def test_protocol_messages_validate_input() -> None:
    with pytest.raises(ValidationError):
        ClaimRequest.model_validate({"queues": [], "job_types": ["x"]})
    with pytest.raises(ValidationError):
        ClaimRequest.model_validate({"queues": ["gpu"], "job_types": ["x"]})
    with pytest.raises(ValidationError):
        FailRequest(code="Mal Código", message="x")
    with pytest.raises(ValidationError):
        OutputDeclaration.model_validate(
            {
                "name": "video",
                "object_id": "00000000-0000-0000-0000-000000000000",
                "sha256": "XYZ",
                "size_bytes": 1,
            }
        )
