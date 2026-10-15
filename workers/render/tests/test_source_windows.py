"""Tramos usados de cada original y desplazamiento de recortes para la composición."""

from __future__ import annotations

from deken_render.source_windows import MARGIN_S, shift_sources, used_windows

A, B = "3b241101-e2bb-4255-8caf-4136c566a962", "0f8fad5b-d9cb-469f-a165-70867728950e"


def _timeline() -> dict[str, object]:
    return {
        "output": {"fps": 30},
        "tracks": [
            {"id": "v", "kind": "video", "clips": [
                {"id": "a1", "asset_id": A, "source_in_s": 120.0, "source_out_s": 125.0},
                {"id": "a2", "asset_id": A, "source_in_s": 300.0, "source_out_s": 302.5},
                {"id": "b1", "asset_id": B, "source_in_s": 0.2, "source_out_s": 4.0},
            ]},
            {"id": "t", "kind": "text", "clips": [{"id": "x", "text": "hola"}]},
            {"id": "m", "kind": "audio", "clips": [
                {"id": "au", "asset_id": A, "source_in_s": 310.0, "duration_frames": 60},
            ]},
        ],
    }  # fmt: skip


def test_used_windows_union_with_margin() -> None:
    windows = used_windows(_timeline())
    # A: de 120 s (vídeo) a 312 s (audio: 310 + 60/30), con margen; B empieza en 0.
    assert windows[A] == (120.0 - MARGIN_S, 312.0 + MARGIN_S)
    assert windows[B] == (0.0, 4.0 + MARGIN_S)
    assert used_windows({"output": {"fps": 30}, "tracks": []}) == {}


def test_shift_sources_only_for_prepared_assets() -> None:
    timeline = _timeline()
    shifted = shift_sources(timeline, {A: 119.5})
    clips = shifted["tracks"][0]["clips"]  # type: ignore[index]
    assert (clips[0]["source_in_s"], clips[0]["source_out_s"]) == (0.5, 5.5)
    assert (clips[1]["source_in_s"], clips[1]["source_out_s"]) == (180.5, 183.0)
    assert clips[2]["source_in_s"] == 0.2  # B no tiene copia: sin cambios
    assert shifted["tracks"][2]["clips"][0]["source_in_s"] == 190.5  # type: ignore[index]
    # La línea de tiempo original (la guardada) no cambia.
    assert timeline["tracks"][0]["clips"][0]["source_in_s"] == 120.0  # type: ignore[index]
    assert shift_sources(timeline, {}) is timeline
