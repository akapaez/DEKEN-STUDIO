/**
 * Reglas semánticas de la línea de tiempo (además del esquema estructural).
 * Las usa el renderer antes de renderizar y, en el futuro, el editor mientras se edita.
 */
import { FORMATS } from "../formats";
import { reframeMatchesOutput } from "./geometry";
import {
  assetKey,
  brandKey,
  MIN_TEXT_PX,
  timelineSchema,
  type ResolvedSources,
  type Timeline,
  videoClipFrames,
} from "./timeline";

export interface TimelineIssue {
  path: string;
  message: string;
}

export const LOGO_NOT_BEFORE_SECONDS = 3;

/** Valida estructura y reglas. Devuelve el documento normalizado o la lista de problemas. */
export function parseTimeline(
  input: unknown,
): { ok: true; timeline: Timeline } | { ok: false; issues: TimelineIssue[] } {
  const parsed = timelineSchema.safeParse(input);
  if (!parsed.success) {
    return {
      ok: false,
      issues: parsed.error.issues.map((i) => ({ path: i.path.join("."), message: i.message })),
    };
  }
  const issues = semanticIssues(parsed.data);
  return issues.length ? { ok: false, issues } : { ok: true, timeline: parsed.data };
}

export function semanticIssues(t: Timeline, sources?: ResolvedSources): TimelineIssue[] {
  const issues: TimelineIssue[] = [];
  const { fps, duration_frames: total } = t.output;
  const output = FORMATS[t.output.format];
  const ids = new Set<string>();

  const within = (path: string, start: number, length: number) => {
    if (start + length > total) issues.push({ path, message: "el clip termina después del final" });
  };

  t.tracks.forEach((track, ti) => {
    const base = `tracks.${ti}`;
    if (ids.has(track.id)) issues.push({ path: `${base}.id`, message: "id de pista repetido" });
    ids.add(track.id);

    if (track.kind === "video") {
      const spans: Array<[number, number, number]> = [];
      track.clips.forEach((clip, ci) => {
        const path = `${base}.clips.${ci}`;
        const length = videoClipFrames(clip, fps);
        within(path, clip.at_frame, length);
        spans.push([clip.at_frame, clip.at_frame + length, clip.transition_in.frames]);
        const source = sources?.[assetKey(clip.asset_id)];
        if (sources && !source) issues.push({ path, message: "medio no resuelto o no autorizado" });
        if (source?.duration_s !== undefined && clip.source_out_s > source.duration_s + 0.05) {
          issues.push({ path, message: "source_out_s supera la duración del original" });
        }
        if (clip.reframe && source?.width && source.height) {
          const ok = reframeMatchesOutput(
            clip.reframe,
            { width: source.width, height: source.height },
            output,
          );
          if (!ok) issues.push({ path: `${path}.reframe`, message: "el reencuadre deformaría la imagen" });
        }
      });
      spans.sort((a, b) => a[0] - b[0]);
      for (let i = 1; i < spans.length; i += 1) {
        const prev = spans[i - 1]!;
        const cur = spans[i]!;
        // Solo pueden solaparse durante la transición de entrada del clip siguiente.
        if (cur[0] < prev[1] - cur[2]) {
          issues.push({ path: `${base}.clips`, message: "clips de vídeo solapados" });
          break;
        }
      }
    }

    if (track.kind === "text") {
      track.clips.forEach((clip, ci) => {
        const path = `${base}.clips.${ci}`;
        within(path, clip.at_frame, clip.duration_frames);
        if (clip.size_px < MIN_TEXT_PX) issues.push({ path, message: `texto por debajo de ${MIN_TEXT_PX} px` });
        // Mínimo de lectura: 2,5 s por línea (guía de animaciones para reels).
        if (clip.animation === "arrive" && clip.duration_frames < Math.round(2.5 * fps)) {
          issues.push({ path, message: "un texto debe verse al menos 2,5 s" });
        }
      });
    }

    if (track.kind === "subtitles") {
      track.cues.forEach((cue, ci) => {
        if (cue.end_frame > total) issues.push({ path: `${base}.cues.${ci}`, message: "subtítulo fuera de la duración" });
      });
    }

    if (track.kind === "brand") {
      track.clips.forEach((clip, ci) => {
        const path = `${base}.clips.${ci}`;
        within(path, clip.at_frame, clip.duration_frames);
        if (clip.at_frame < LOGO_NOT_BEFORE_SECONDS * fps) {
          issues.push({ path, message: "el logo no puede aparecer en los 3 primeros segundos" });
        }
        if (sources && !sources[brandKey(clip.brand_asset_id)]) {
          issues.push({ path, message: "recurso de marca no resuelto o no autorizado" });
        }
      });
    }

    if (track.kind === "audio") {
      track.clips.forEach((clip, ci) => {
        const path = `${base}.clips.${ci}`;
        within(path, clip.at_frame, clip.duration_frames);
        if (track.role === "music" && !clip.license_ref) {
          issues.push({ path, message: "la música necesita referencia de licencia" });
        }
      });
    }
  });
  return issues;
}
