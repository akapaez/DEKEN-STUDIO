/**
 * Línea de tiempo v1 (`deken.timeline/1`): documento JSON versionado que interpretan
 * igual la previsualización (Remotion Player en la web) y el render final (worker).
 *
 * - Posiciones y duraciones en FOTOGRAMAS a la tasa de salida (sin errores de redondeo).
 * - Recortes de origen en SEGUNDOS del original.
 * - Las referencias a medios son IDs (`asset_id`, `brand_asset_id`); las URLs reales las
 *   resuelve el sistema en cada render y NUNCA se guardan en el documento.
 *
 * Este esquema (zod) es la fuente única: `scripts/generate-schema.ts` genera el JSON
 * Schema que valida la API (Python). Las reglas semánticas viven en `validate.ts`.
 */
import { z } from "zod";

import { FORMATS, type FormatId } from "../formats";

export const TIMELINE_SCHEMA_ID = "deken.timeline/1";
export const MAX_DURATION_SECONDS = 10 * 60;
export const MIN_TEXT_PX = 30;

const id = z.string().regex(/^[a-z0-9][a-z0-9_-]{0,63}$/, "id no válido");
const uuid = z.string().uuid();
const frames = z.number().int().min(0);
const positiveFrames = z.number().int().min(1);
const unit = z.number().min(0).max(1);

export const reframeSchema = z
  .object({ x: unit, y: unit, w: z.number().gt(0).max(1), h: z.number().gt(0).max(1) })
  .strict()
  .refine((r) => r.x + r.w <= 1.0001 && r.y + r.h <= 1.0001, "el reencuadre se sale de la imagen");

export const transitionSchema = z
  .object({
    type: z.enum(["cut", "fade", "wipe"]),
    frames: z.number().int().min(0).max(60),
  })
  .strict();

export const videoClipSchema = z
  .object({
    id,
    asset_id: uuid,
    source_in_s: z.number().min(0),
    source_out_s: z.number().gt(0),
    at_frame: frames,
    speed: z.number().min(0.25).max(4).default(1),
    /** Rectángulo normalizado del original que llena el fotograma. null = encuadre centrado. */
    reframe: reframeSchema.nullable().default(null),
    /** cover: llena el fotograma recortando; contain: imagen completa con fondo de marca. */
    fit: z.enum(["cover", "contain"]).default("cover"),
    volume: z.number().min(0).max(1).default(1),
    fade_in_frames: frames.max(60).default(0),
    fade_out_frames: frames.max(60).default(0),
    transition_in: transitionSchema.default({ type: "cut", frames: 0 }),
  })
  .strict()
  .refine((c) => c.source_out_s > c.source_in_s, "source_out_s debe ser mayor que source_in_s");

export const textClipSchema = z
  .object({
    id,
    text: z.string().min(1).max(200),
    at_frame: frames,
    duration_frames: positiveFrames,
    style: z.enum(["headline", "title", "body", "label"]).default("title"),
    size_px: z.number().int().min(MIN_TEXT_PX).max(220).default(96),
    weight: z.union([z.literal(600), z.literal(700), z.literal(800), z.literal(900)]).default(900),
    position: z.enum(["top", "center", "bottom"]).default("center"),
    align: z.enum(["left", "center"]).default("left"),
    color: z.enum(["white", "ink", "green"]).default("white"),
    /** Caja opaca detrás del texto (obligatoria sobre metraje, ver guía de marca). */
    box: z.boolean().default(true),
    animation: z.enum(["arrive", "none"]).default("arrive"),
    /** Hechos verificados que respaldan el texto (Sprint 2). */
    fact_ids: z.array(uuid).max(20).default([]),
  })
  .strict();

export const subtitleCueSchema = z
  .object({ start_frame: frames, end_frame: positiveFrames, text: z.string().min(1).max(160) })
  .strict()
  .refine((c) => c.end_frame > c.start_frame, "end_frame debe ser mayor que start_frame");

export const brandClipSchema = z
  .object({
    id,
    brand_asset_id: uuid,
    at_frame: frames,
    duration_frames: positiveFrames,
    corner: z.enum(["top_left", "top_right", "bottom_left", "bottom_right", "center"]).default("bottom_right"),
    width_px: z.number().int().min(80).max(1600).default(320),
  })
  .strict();

export const audioClipSchema = z
  .object({
    id,
    asset_id: uuid.optional(),
    brand_asset_id: uuid.optional(),
    source_in_s: z.number().min(0).default(0),
    at_frame: frames,
    duration_frames: positiveFrames,
    volume: z.number().min(0).max(1).default(1),
    /** Referencia de la licencia (obligatoria para música). */
    license_ref: z.string().min(1).max(200).optional(),
  })
  .strict()
  .refine((c) => Boolean(c.asset_id) !== Boolean(c.brand_asset_id), "indica asset_id o brand_asset_id");

export const trackSchema = z.discriminatedUnion("kind", [
  z.object({ id, kind: z.literal("video"), clips: z.array(videoClipSchema).max(500) }).strict(),
  z.object({ id, kind: z.literal("text"), clips: z.array(textClipSchema).max(500) }).strict(),
  z
    .object({
      id,
      kind: z.literal("subtitles"),
      size_px: z.number().int().min(MIN_TEXT_PX).max(96).default(48),
      cues: z.array(subtitleCueSchema).max(2000),
    })
    .strict(),
  z.object({ id, kind: z.literal("brand"), clips: z.array(brandClipSchema).max(50) }).strict(),
  z
    .object({
      id,
      kind: z.literal("audio"),
      role: z.enum(["original", "narration", "music"]),
      clips: z.array(audioClipSchema).max(200),
    })
    .strict(),
]);

/**
 * Salida: el formato fija el tamaño exacto (literal en el JSON Schema, no solo un refine),
 * así la API rechaza un 9:16 que no sea 1080×1920 sin esperar al motor.
 */
const fpsSchema = z.union([z.literal(24), z.literal(25), z.literal(30), z.literal(60)]);
const outputFor = <F extends FormatId>(format: F) =>
  z
    .object({
      format: z.literal(format),
      width: z.literal(FORMATS[format].width),
      height: z.literal(FORMATS[format].height),
      fps: fpsSchema,
      // Tope absoluto representable en JSON Schema (60 fps); el tope por fps va en el refine.
      duration_frames: positiveFrames.max(MAX_DURATION_SECONDS * 60),
    })
    .strict();

export const outputSchema = z
  .discriminatedUnion("format", [
    outputFor("vertical_9_16"),
    outputFor("horizontal_16_9"),
    outputFor("square_1_1"),
  ])
  .refine((o) => o.duration_frames <= MAX_DURATION_SECONDS * o.fps, "duración máxima superada");

export const timelineSchema = z
  .object({
    schema: z.literal(TIMELINE_SCHEMA_ID),
    template: z.string().regex(/^[a-z0-9_]{1,64}$/).optional(),
    output: outputSchema,
    tracks: z.array(trackSchema).max(32),
  })
  .strict();

export type Timeline = z.infer<typeof timelineSchema>;
export type TimelineInput = z.input<typeof timelineSchema>;
export type Track = Timeline["tracks"][number];
export type VideoClip = z.infer<typeof videoClipSchema>;
export type TextClip = z.infer<typeof textClipSchema>;
export type BrandClip = z.infer<typeof brandClipSchema>;
export type AudioClip = z.infer<typeof audioClipSchema>;
export type Reframe = z.infer<typeof reframeSchema>;

export function emptyTimeline(format: FormatId, seconds: number, fps: 24 | 25 | 30 | 60 = 30): Timeline {
  const f = FORMATS[format];
  return {
    schema: TIMELINE_SCHEMA_ID,
    output: { format, width: f.width, height: f.height, fps, duration_frames: Math.round(seconds * fps) },
    tracks: [],
  };
}

/** Duración en fotogramas de salida de un clip de vídeo. */
export function videoClipFrames(clip: VideoClip, fps: number): number {
  return Math.max(1, Math.round(((clip.source_out_s - clip.source_in_s) / clip.speed) * fps));
}

/**
 * Medios resueltos para un render concreto (no se guardan en el documento).
 * Clave: `asset:<uuid>` o `brand:<uuid>`.
 */
export const resolvedSourceSchema = z
  .object({
    src: z.string().min(1),
    kind: z.enum(["video", "image", "audio"]),
    width: z.number().int().positive().optional(),
    height: z.number().int().positive().optional(),
    duration_s: z.number().positive().optional(),
    has_audio: z.boolean().optional(),
  })
  .strict();

export type ResolvedSource = z.infer<typeof resolvedSourceSchema>;
export type ResolvedSources = Record<string, ResolvedSource>;

export const assetKey = (assetId: string) => `asset:${assetId}`;
export const brandKey = (brandAssetId: string) => `brand:${brandAssetId}`;
