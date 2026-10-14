"""Unidades de la biblioteca y la marca: proxys, cadencias, etiquetas, análisis de logos,
tipografías y validación de la línea de tiempo (sin servicios externos)."""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

from deken_api.errors import ApiError
from deken_api.security.rbac import ROLE_PERMISSIONS, Permission, Role
from deken_api.services.brand import (
    analyze_font,
    analyze_logo,
    declared_color_from_name,
    family_from_ratio,
)
from deken_api.services.media import (
    normalize_tags,
    orientation_of,
    proxy_size,
    snap_fps,
    usable_for_production,
)
from deken_api.services.renders import referenced_ids, schema_issues
from deken_api.testing import synthetic_font, synthetic_logo


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((1080, 1920), (540, 960)),
        ((3840, 2160), (960, 540)),
        ((1440, 1080), (720, 540)),
        ((480, 360), (480, 360)),  # nunca se amplía
        ((1079, 1921), (540, 962)),  # dimensiones pares para H.264
    ],
)
def test_proxy_size_keeps_aspect_without_upscaling(
    size: tuple[int, int], expected: tuple[int, int]
) -> None:
    width, height = proxy_size(*size)
    assert (width, height) == expected
    assert width % 2 == 0 and height % 2 == 0
    assert abs(width / height - size[0] / size[1]) < 0.01


@pytest.mark.parametrize(
    ("fps", "expected"),
    [(29.97002997, 29.97), (30.02, 30.0), (24.0, 24.0), (59.94, 59.94), (120.0, 60.0),
     (None, 30.0), (0, 30.0), (12.5, 12.5)],
)  # fmt: skip
def test_snap_fps(fps: float | None, expected: float) -> None:
    assert snap_fps(fps) == expected


def test_normalize_tags() -> None:
    assert normalize_tags(["  Fábrica ", "fábrica", "Línea  2", ""]) == ["fábrica", "línea 2"]
    with pytest.raises(ApiError):
        normalize_tags(["<script>"])
    with pytest.raises(ApiError):
        normalize_tags([f"t{i}" for i in range(31)])


def test_orientation() -> None:
    assert orientation_of(1080, 1920) == "vertical"
    assert orientation_of(1920, 1080) == "horizontal"
    assert orientation_of(1080, 1060) == "square"
    assert orientation_of(None, 1080) is None


def _asset(**kw: Any) -> Any:
    base = {"status": "ready", "archived_at": None, "people_present": "unknown",
            "consent_status": "pending"}  # fmt: skip
    return SimpleNamespace(**{**base, **kw})


def test_usable_for_production_requires_rights() -> None:
    assert usable_for_production(_asset()) is False
    assert usable_for_production(_asset(people_present="no")) is True
    assert usable_for_production(_asset(people_present="yes", consent_status="granted")) is True
    assert usable_for_production(_asset(people_present="no", consent_status="denied")) is False
    assert usable_for_production(_asset(status="processing", people_present="no")) is False


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("GRUPO-DEKEN-HORIZONTAL-BLANCO.png", "blanco"),
        ("DEKEN-VERDE-GRIS.png", "verde-gris"),
        ("gd_gris.webp", "gris"),
        ("logo.png", None),
        ("VERDEMAR.png", None),
    ],
)
def test_declared_color_from_name(name: str, expected: str | None) -> None:
    assert declared_color_from_name(name) == expected


def test_family_from_ratio() -> None:
    assert family_from_ratio(5.2) == "DEKEN"
    assert family_from_ratio(1.3) == "GD"
    assert family_from_ratio(2.2) == "GRUPO-DEKEN"
    assert family_from_ratio(11.4) == "GRUPO-DEKEN-HORIZONTAL"
    assert family_from_ratio(3.6) is None


def test_analyze_logo_measures_inks(tmp_path: Path) -> None:
    path = synthetic_logo(
        tmp_path / "l.png", width=520, height=100, inks=[("#76B82A", 0.7), ("#383E42", 0.3)]
    )
    info, preview = analyze_logo(path.read_bytes())
    assert (info.width, info.height, info.aspect_ratio) == (520, 100, 5.2)
    assert info.measured_name == "verde-gris"
    assert info.measured_hex == "#76B82A"
    assert info.recommended_background == "light"
    assert info.family_guess == "DEKEN"
    assert info.has_alpha is True
    assert Image.open(io.BytesIO(preview)).format == "PNG"

    white = synthetic_logo(tmp_path / "w.png", width=200, height=200, inks=[("#FFFFFF", 1)])
    assert analyze_logo(white.read_bytes())[0].recommended_background == "dark"


def test_analyze_logo_rejects_garbage_and_transparent() -> None:
    with pytest.raises(ApiError):
        analyze_logo(b"no es una imagen")
    buf = io.BytesIO()
    Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(buf, format="PNG")
    with pytest.raises(ApiError, match="transparente"):
        analyze_logo(buf.getvalue())


def test_analyze_font(tmp_path: Path) -> None:
    info = analyze_font(
        synthetic_font(tmp_path / "f.ttf", family="Prueba Sintetica", weight=700).read_bytes()
    )
    assert (info.family, info.style, info.weight, info.italic) == (
        "Prueba Sintetica",
        "Black",
        700,
        False,
    )
    with pytest.raises(ApiError):
        analyze_font(b"\x00\x01\x00\x00" + b"\x00" * 32)


def _timeline(**output: Any) -> dict[str, Any]:
    return {
        "schema": "deken.timeline/1",
        "output": {"format": "vertical_9_16", "width": 1080, "height": 1920, "fps": 30,
                   "duration_frames": 150, **output},
        "tracks": [],
    }  # fmt: skip


def test_timeline_json_schema() -> None:
    assert schema_issues(_timeline()) == []
    assert schema_issues(_timeline(width=1920))  # 9:16 debe ser 1080x1920
    assert schema_issues(_timeline(fps=29))
    assert schema_issues({**_timeline(), "schema": "deken.timeline/2"})
    assert schema_issues({**_timeline(), "extra": True})
    bad_clip = _timeline()
    bad_clip["tracks"] = [{"id": "t", "kind": "text", "clips": [
        {"id": "a", "text": "x", "at_frame": 0, "duration_frames": 90, "size_px": 20},
    ]}]  # fmt: skip
    issues = schema_issues(bad_clip)
    assert issues and issues[0]["path"].startswith("tracks.0")


def test_referenced_ids() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    timeline = _timeline()
    timeline["tracks"] = [
        {"id": "v", "kind": "video", "clips": [{"asset_id": str(a)}, {"asset_id": str(a)}]},
        {"id": "m", "kind": "brand", "clips": [{"brand_asset_id": str(b)}]},
    ]
    assert referenced_ids(timeline) == ({a}, {b})


def test_sprint1_permissions() -> None:
    editor, reviewer, viewer = (
        ROLE_PERMISSIONS[r] for r in (Role.EDITOR, Role.REVIEWER, Role.VIEWER)
    )
    assert {Permission.MEDIA_WRITE, Permission.RENDER_CREATE} <= editor
    assert Permission.MEDIA_RIGHTS not in editor
    assert Permission.BRAND_MANAGE not in editor
    assert Permission.MEDIA_RIGHTS in reviewer
    assert {Permission.MEDIA_READ, Permission.BRAND_READ} <= viewer
    assert not {Permission.MEDIA_WRITE, Permission.RENDER_CREATE} & viewer
    assert set(Permission) == ROLE_PERMISSIONS[Role.ADMIN]
