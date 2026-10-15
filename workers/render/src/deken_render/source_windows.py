"""Tramos de cada original que usa una línea de tiempo `deken.timeline/1`.

Sirven para preparar solo lo necesario antes de componer (p. ej. la copia SDR de un
original HDR): de un original de 10 minutos del que se usan 5 segundos se convierten
5 segundos más un margen. Después se desplazan los recortes de origen de las propiedades
que recibe la composición; la línea de tiempo guardada no cambia.
"""

from __future__ import annotations

import copy
from typing import Any

MARGIN_S = 0.5


def used_windows(timeline: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """`{asset_id: (inicio_s, fin_s)}` con la unión de los tramos usados (vídeo y audio)."""
    fps = float(timeline.get("output", {}).get("fps") or 30)
    windows: dict[str, tuple[float, float]] = {}

    def add(asset_id: str, start: float, end: float) -> None:
        lo, hi = windows.get(asset_id, (start, end))
        windows[asset_id] = (min(lo, start), max(hi, end))

    for track in timeline.get("tracks", []):
        for clip in track.get("clips", []):
            asset_id = clip.get("asset_id")
            if not asset_id:
                continue
            start = float(clip.get("source_in_s") or 0)
            if track.get("kind") == "video":
                end = float(clip["source_out_s"])
            elif track.get("kind") == "audio":
                end = start + float(clip["duration_frames"]) / fps
            else:
                continue
            add(str(asset_id), start, end)
    return {
        asset_id: (max(0.0, start - MARGIN_S), end + MARGIN_S)
        for asset_id, (start, end) in windows.items()
    }


def shift_sources(timeline: dict[str, Any], offsets: dict[str, float]) -> dict[str, Any]:
    """Copia de la línea de tiempo con los recortes de origen relativos al tramo preparado."""
    if not offsets:
        return timeline
    shifted = copy.deepcopy(timeline)
    for track in shifted.get("tracks", []):
        for clip in track.get("clips", []):
            offset = offsets.get(str(clip.get("asset_id")))
            if not offset:
                continue
            clip["source_in_s"] = round(float(clip.get("source_in_s") or 0) - offset, 6)
            if "source_out_s" in clip:
                clip["source_out_s"] = round(float(clip["source_out_s"]) - offset, 6)
    return shifted
