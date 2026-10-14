/**
 * Motor de render Remotion: valida, resuelve medios locales, construye la composición,
 * renderiza (H.264 + AAC, yuv420p) con progreso y cancelación.
 */
import { existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, isAbsolute } from "node:path";

import {
  type ResolvedSources,
  parseTimeline,
  semanticIssues,
  evaluationPropsSchema,
} from "@deken/video-compositions/schema";
import { type CancelSignal, renderMedia, selectComposition } from "@remotion/renderer";

import { confined, startInputServer } from "./server.js";
import { licenseFor, RenderError, type RenderSpec } from "./spec.js";

export interface RenderProgress {
  progress: number;
  stage: string;
  rendered_frames: number;
  encoded_frames: number;
}

export interface RenderResult {
  output_path: string;
  size_bytes: number;
  composition: string;
  width: number;
  height: number;
  fps: number;
  duration_frames: number;
  purpose: string;
  license_mode: string;
  render_ms: number;
}

function resolveSources(spec: RenderSpec, urlFor: (file: string) => string): ResolvedSources {
  const sources: ResolvedSources = {};
  for (const input of spec.inputs) {
    if (isAbsolute(input.file)) throw new RenderError("unsafe_path", "Las entradas deben ser relativas");
    confined(spec.work_dir, input.file); // lanza si la ruta escapa del directorio del trabajo
    sources[input.key] = {
      src: urlFor(input.file),
      kind: input.kind,
      width: input.width,
      height: input.height,
      duration_s: input.duration_s,
      has_audio: input.has_audio,
    };
  }
  return sources;
}

export async function runRender(
  spec: RenderSpec,
  onProgress: (p: RenderProgress) => void,
  cancelSignal?: CancelSignal,
): Promise<RenderResult> {
  const license = licenseFor(spec);
  if (!existsSync(`${spec.bundle_dir}/index.html`)) {
    throw new RenderError("bundle_missing", `No existe el bundle de composiciones en ${spec.bundle_dir}`);
  }
  const server = await startInputServer(spec.work_dir);
  try {
    const sources = resolveSources(spec, server.urlFor);
    let inputProps: Record<string, unknown>;
    if (spec.composition === "DekenTimeline") {
      const parsed = parseTimeline(spec.props.timeline);
      if (!parsed.ok) throw new RenderError("invalid_timeline", "Línea de tiempo no válida", parsed.issues);
      const issues = semanticIssues(parsed.timeline, sources);
      if (issues.length) throw new RenderError("invalid_timeline", "Línea de tiempo no válida", issues);
      inputProps = { timeline: parsed.timeline, sources, evaluation: spec.purpose !== "production" };
    } else {
      const parsed = evaluationPropsSchema.safeParse(spec.props);
      if (!parsed.success) {
        throw new RenderError("invalid_props", "Propiedades no válidas", parsed.error.issues);
      }
      if (spec.purpose !== "evaluation") {
        throw new RenderError("invalid_props", "La composición de evaluación solo admite propósito de evaluación");
      }
      inputProps = parsed.data;
    }

    const browserExecutable = spec.browser_executable ?? null;
    const composition = await selectComposition({
      serveUrl: spec.bundle_dir,
      id: spec.composition,
      inputProps,
      browserExecutable,
      timeoutInMilliseconds: spec.timeout_ms,
      logLevel: "warn",
    });
    mkdirSync(dirname(spec.output_path), { recursive: true });
    const started = Date.now();
    await renderMedia({
      composition,
      serveUrl: spec.bundle_dir,
      codec: "h264",
      pixelFormat: "yuv420p",
      audioCodec: "aac",
      enforceAudioTrack: true,
      crf: 18,
      x264Preset: "medium",
      colorSpace: "bt709",
      outputLocation: spec.output_path,
      inputProps,
      browserExecutable,
      concurrency: spec.concurrency ?? null,
      timeoutInMilliseconds: spec.timeout_ms,
      cancelSignal,
      overwrite: true,
      logLevel: "warn",
      chromiumOptions: { gl: "swangle" },
      licenseKey: license.licenseKey,
      isProduction: license.isProduction,
      onProgress: (p) =>
        onProgress({
          progress: p.progress,
          stage: p.stitchStage,
          rendered_frames: p.renderedFrames,
          encoded_frames: p.encodedFrames,
        }),
    });
    return {
      output_path: spec.output_path,
      size_bytes: statSync(spec.output_path).size,
      composition: spec.composition,
      width: composition.width,
      height: composition.height,
      fps: composition.fps,
      duration_frames: composition.durationInFrames,
      purpose: spec.purpose,
      license_mode: spec.license.mode,
      render_ms: Date.now() - started,
    };
  } finally {
    await server.close();
  }
}
