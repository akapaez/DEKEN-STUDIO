"""Resumen de ffprobe y verificación de especificaciones de vídeo.

Lo usan tanto los workers (comprobación antes de subir) como la API (verificación
independiente del objeto ya almacenado). Una salida solo es válida si cumple la
especificación pedida: se mide, no se supone.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SQUARE_PIXELS = {"1:1"}
MAX_VIDEO_SECONDS = 6 * 3600
"""Duración máxima de un vídeo (biblioteca y renders). La ingesta tiene 6 h de límite."""
DynamicRange = Literal["sdr", "hlg", "pq"]
HDR_TRANSFERS: dict[str, DynamicRange] = {"arib-std-b67": "hlg", "smpte2084": "pq"}
"""Relaciones de aspecto de píxel aceptadas: la salida nunca se deforma."""


class VideoSpec(BaseModel):
    """Especificación de un fichero de vídeo de salida."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    container: Literal["mp4"] = "mp4"
    width: int = Field(default=1080, ge=16, le=7680)
    height: int = Field(default=1920, ge=16, le=7680)
    fps: float = Field(default=30, ge=1, le=120)
    video_codec: Literal["h264"] = "h264"
    pix_fmt: Literal["yuv420p"] = "yuv420p"
    audio_codec: Literal["aac"] | None = "aac"
    audio_sample_rate: int | None = Field(default=48000, ge=8000, le=192000)
    duration_s: float = Field(gt=0, le=MAX_VIDEO_SECONDS)
    # Proporcionales a la duración en los proxys (1 %): vídeos de horas necesitan margen.
    frame_tolerance: int = Field(
        default=1, ge=0, le=100_000, description="Diferencia máxima de fotogramas de vídeo"
    )
    container_tolerance_s: float = Field(
        default=0.1,
        ge=0,
        le=600,
        description="Margen para la duración del contenedor (bloques AAC, edit lists)",
    )

    @property
    def expected_frames(self) -> int:
        return round(self.duration_s * self.fps)


class ImageSpec(BaseModel):
    """Especificación mínima de una imagen derivada (miniatura, póster, tira)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    codecs: tuple[str, ...] = ("mjpeg", "png", "webp")
    max_width: int = Field(default=8192, ge=1)
    max_height: int = Field(default=8192, ge=1)


class StreamSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    codec_type: str
    codec_name: str | None = None
    profile: str | None = None
    width: int | None = None
    height: int | None = None
    pix_fmt: str | None = None
    sample_aspect_ratio: str | None = None
    display_aspect_ratio: str | None = None
    avg_frame_rate: float | None = None
    r_frame_rate: float | None = None
    nb_frames: int | None = None
    duration_s: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bit_rate: int | None = None
    rotation: int | None = None
    """Rotación de visualización en grados (metadato del móvil): 0, 90, 180 o 270."""
    color_transfer: str | None = None
    color_primaries: str | None = None
    color_space: str | None = None

    @property
    def dynamic_range(self) -> DynamicRange | None:
        """`hlg` / `pq` si el vídeo es HDR (típico de móviles recientes); `sdr` si no."""
        if self.codec_type != "video":
            return None
        return HDR_TRANSFERS.get(self.color_transfer or "", "sdr")

    @property
    def display_size(self) -> tuple[int, int] | None:
        """Tamaño tal como se ve: aplica relación de aspecto de píxel y rotación."""
        if not self.width or not self.height:
            return None
        width, height = self.width, self.height
        sar = parse_ratio(self.sample_aspect_ratio)
        if sar and abs(sar - 1) > 1e-3:
            width = round(width * sar)
        if self.rotation in (90, 270):
            width, height = height, width
        return width, height


class ProbeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format_name: str
    format_long_name: str | None = None
    duration_s: float | None = None
    size_bytes: int | None = None
    bit_rate: int | None = None
    streams: list[StreamSummary]

    @property
    def video_streams(self) -> list[StreamSummary]:
        return [s for s in self.streams if s.codec_type == "video"]

    @property
    def audio_streams(self) -> list[StreamSummary]:
        return [s for s in self.streams if s.codec_type == "audio"]


def parse_ratio(value: object) -> float | None:
    """'16:9' → 1.777…; '0:1' o valores no válidos → None."""
    if not isinstance(value, str) or ":" not in value:
        return None
    num, _, den = value.partition(":")
    try:
        n, d = int(num), int(den)
    except ValueError:
        return None
    if n <= 0 or d <= 0:
        return None
    return n / d


def _rotation(raw: dict[str, Any]) -> int | None:
    """Rotación normalizada (0/90/180/270) desde la matriz de visualización o la etiqueta."""
    value: object = None
    for side in raw.get("side_data_list") or []:
        if isinstance(side, dict) and "rotation" in side:
            value = side["rotation"]
            break
    if value is None:
        tags = raw.get("tags")
        if isinstance(tags, dict):
            value = tags.get("rotate")
    try:
        degrees = round(float(str(value)))
    except (TypeError, ValueError):
        return None
    return degrees % 360 if degrees % 90 == 0 else None


def parse_rate(value: object) -> float | None:
    """Convierte '30000/1001' o '30/1' en float. Devuelve None si no es válido."""
    if not isinstance(value, str) or not value:
        return None
    try:
        frac = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    if frac <= 0:
        return None
    return float(frac)


def _int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def _str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _color(value: object) -> str | None:
    text = _str(value)
    return None if text in (None, "unknown", "reserved") else text


def parse_ffprobe_json(data: dict[str, Any]) -> ProbeSummary:
    """Convierte la salida de `ffprobe -show_format -show_streams -of json`."""
    fmt = data.get("format")
    if not isinstance(fmt, dict) or not fmt.get("format_name"):
        raise ValueError("ffprobe no devolvió información de formato")
    streams_raw = data.get("streams") or []
    streams: list[StreamSummary] = []
    for raw in streams_raw:
        if not isinstance(raw, dict):
            continue
        streams.append(
            StreamSummary(
                index=_int(raw.get("index")) or 0,
                codec_type=str(raw.get("codec_type") or "unknown"),
                codec_name=_str(raw.get("codec_name")),
                profile=_str(raw.get("profile")),
                width=_int(raw.get("width")),
                height=_int(raw.get("height")),
                pix_fmt=_str(raw.get("pix_fmt")),
                sample_aspect_ratio=_str(raw.get("sample_aspect_ratio")),
                display_aspect_ratio=_str(raw.get("display_aspect_ratio")),
                avg_frame_rate=parse_rate(raw.get("avg_frame_rate")),
                r_frame_rate=parse_rate(raw.get("r_frame_rate")),
                nb_frames=_int(raw.get("nb_frames")),
                duration_s=_float(raw.get("duration")),
                sample_rate=_int(raw.get("sample_rate")),
                channels=_int(raw.get("channels")),
                bit_rate=_int(raw.get("bit_rate")),
                rotation=_rotation(raw),
                color_transfer=_color(raw.get("color_transfer")),
                color_primaries=_color(raw.get("color_primaries")),
                color_space=_color(raw.get("color_space")),
            )
        )
    return ProbeSummary(
        format_name=str(fmt["format_name"]),
        format_long_name=_str(fmt.get("format_long_name")),
        duration_s=_float(fmt.get("duration")),
        size_bytes=_int(fmt.get("size")),
        bit_rate=_int(fmt.get("bit_rate")),
        streams=streams,
    )


def check_video_spec(summary: ProbeSummary, spec: VideoSpec) -> list[str]:
    """Devuelve la lista de incumplimientos (vacía si el fichero es válido)."""
    problems: list[str] = []

    if spec.container not in summary.format_name.split(","):
        problems.append(f"contenedor '{summary.format_name}' no es {spec.container}")

    videos = summary.video_streams
    if len(videos) != 1:
        problems.append(f"se esperaba 1 pista de vídeo y hay {len(videos)}")
    else:
        v = videos[0]
        if v.codec_name != spec.video_codec:
            problems.append(f"códec de vídeo '{v.codec_name}' no es {spec.video_codec}")
        if (v.width, v.height) != (spec.width, spec.height):
            problems.append(f"resolución {v.width}x{v.height} no es {spec.width}x{spec.height}")
        if v.pix_fmt != spec.pix_fmt:
            problems.append(f"formato de píxel '{v.pix_fmt}' no es {spec.pix_fmt}")
        if v.sample_aspect_ratio and v.sample_aspect_ratio not in SQUARE_PIXELS:
            problems.append(
                f"relación de aspecto de píxel {v.sample_aspect_ratio} (imagen deformada)"
            )
        if v.avg_frame_rate is None or abs(v.avg_frame_rate - spec.fps) > 0.02:
            problems.append(f"fps {v.avg_frame_rate} no es {spec.fps}")
        if v.nb_frames is None:
            problems.append("no se puede contar el número de fotogramas")
        elif abs(v.nb_frames - spec.expected_frames) > spec.frame_tolerance:
            problems.append(
                f"{v.nb_frames} fotogramas, se esperaban {spec.expected_frames}"
                f" (±{spec.frame_tolerance})"
            )

    audios = summary.audio_streams
    if spec.audio_codec is None:
        if audios:
            problems.append("hay pista de audio y no se esperaba")
    elif len(audios) != 1:
        problems.append(f"se esperaba 1 pista de audio y hay {len(audios)}")
    else:
        a = audios[0]
        if a.codec_name != spec.audio_codec:
            problems.append(f"códec de audio '{a.codec_name}' no es {spec.audio_codec}")
        if spec.audio_sample_rate and a.sample_rate != spec.audio_sample_rate:
            problems.append(f"frecuencia de audio {a.sample_rate} no es {spec.audio_sample_rate}")
        if a.duration_s is not None and abs(a.duration_s - spec.duration_s) > (
            spec.container_tolerance_s
        ):
            problems.append(
                f"duración de audio {a.duration_s:.3f}s fuera de {spec.duration_s}s"
                f" ±{spec.container_tolerance_s}s (posible desincronía)"
            )

    if summary.duration_s is None:
        problems.append("el contenedor no declara duración")
    elif abs(summary.duration_s - spec.duration_s) > spec.container_tolerance_s:
        problems.append(
            f"duración {summary.duration_s:.3f}s fuera de {spec.duration_s}s"
            f" ±{spec.container_tolerance_s}s"
        )

    return problems


def check_image_spec(summary: ProbeSummary, spec: ImageSpec) -> list[str]:
    problems: list[str] = []
    videos = summary.video_streams
    if len(videos) != 1:
        return [f"se esperaba una imagen y hay {len(videos)} pistas de imagen"]
    v = videos[0]
    if v.codec_name not in spec.codecs:
        problems.append(f"formato de imagen '{v.codec_name}' no admitido")
    if not v.width or not v.height:
        problems.append("la imagen no tiene dimensiones")
    elif v.width > spec.max_width or v.height > spec.max_height:
        problems.append(f"imagen de {v.width}x{v.height} demasiado grande")
    return problems
