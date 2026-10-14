/**
 * Composición genérica que interpreta una línea de tiempo `deken.timeline/1`.
 *
 * La MISMA composición se usa en la previsualización (Remotion Player) y en el render
 * final: lo que se ve es lo que se exporta. Los medios llegan resueltos en `sources`
 * (URLs locales del worker o URLs firmadas del proxy en la web), nunca en el documento.
 */
import { brand, neutralsDark, onGreen } from "@deken/brand";
import type { CSSProperties } from "react";
import {
  AbsoluteFill,
  Audio,
  type CalculateMetadataFunction,
  Img,
  interpolate,
  OffthreadVideo,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { ArrivingText } from "../components/primitives";
import { BRAND_FONT_STACK, MONO_FONT_STACK, ensureBrandFonts } from "../fonts";
import { FORMATS } from "../formats";
import { centeredCoverReframe, placeContain, placeReframe } from "../schema/geometry";
import {
  assetKey,
  brandKey,
  type BrandClip,
  type ResolvedSources,
  type TextClip,
  type Timeline,
  timelineSchema,
  type VideoClip,
  videoClipFrames,
} from "../schema/timeline";

export const TIMELINE_ID = "DekenTimeline";

export interface TimelineProps extends Record<string, unknown> {
  timeline: Timeline;
  sources: ResolvedSources;
  /** Renders de evaluación: marca de agua visible "EVALUACIÓN TÉCNICA · NO PUBLICAR". */
  evaluation: boolean;
}

export const timelineMetadata: CalculateMetadataFunction<TimelineProps> = ({ props }) => {
  const t = timelineSchema.parse(props.timeline);
  return {
    width: t.output.width,
    height: t.output.height,
    fps: t.output.fps,
    durationInFrames: t.output.duration_frames,
    props: { ...props, timeline: t },
  };
};

function fadeOpacity(frame: number, length: number, fadeIn: number, fadeOut: number): number {
  const a = fadeIn > 0 ? interpolate(frame, [0, fadeIn], [0, 1], { extrapolateRight: "clamp" }) : 1;
  const b =
    fadeOut > 0
      ? interpolate(frame, [length - fadeOut, length], [1, 0], { extrapolateLeft: "clamp" })
      : 1;
  return Math.min(a, b);
}

function VideoLayer({ clip, sources, length }: { clip: VideoClip; sources: ResolvedSources; length: number }) {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const source = sources[assetKey(clip.asset_id)];
  if (!source) throw new Error(`Medio no resuelto: ${clip.asset_id}`);
  const src = { width: source.width ?? width, height: source.height ?? height };
  const out = { width, height };
  const place =
    clip.fit === "contain" ? placeContain(src, out) : placeReframe(clip.reframe ?? centeredCoverReframe(src, out), src, out);
  const transition = clip.transition_in;
  let opacity = fadeOpacity(frame, length, clip.fade_in_frames, clip.fade_out_frames);
  let clipPath: string | undefined;
  if (transition.type === "fade" && transition.frames > 0) {
    opacity = Math.min(opacity, interpolate(frame, [0, transition.frames], [0, 1], { extrapolateRight: "clamp" }));
  }
  if (transition.type === "wipe" && transition.frames > 0) {
    const p = interpolate(frame, [0, transition.frames], [100, 0], { extrapolateRight: "clamp" });
    clipPath = `inset(0 0 0 ${p}%)`;
  }
  const style: CSSProperties = {
    position: "absolute",
    left: place.left,
    top: place.top,
    width: place.width,
    height: place.height,
    // Mismo factor en ambos ejes: object-fit "fill" sobre una caja con la proporción original.
    objectFit: "fill",
  };
  return (
    <AbsoluteFill style={{ backgroundColor: neutralsDark.background, opacity, clipPath, overflow: "hidden" }}>
      <OffthreadVideo
        src={source.src}
        style={style}
        trimBefore={Math.round(clip.source_in_s * fps)}
        playbackRate={clip.speed}
        volume={clip.volume}
        muted={clip.volume === 0}
      />
    </AbsoluteFill>
  );
}

const TEXT_COLORS = { white: neutralsDark.text, ink: neutralsDark.background, green: brand.green } as const;

/**
 * Banda inferior reservada a los subtítulos (hasta 2 líneas + caja + separación). Los
 * textos y logos colocados abajo quedan por encima: nunca se tapan entre sí.
 */
export function subtitleBand(t: Pick<Timeline, "tracks">): number {
  const sizes = t.tracks.flatMap((tr) => (tr.kind === "subtitles" && tr.cues.length ? [tr.size_px] : []));
  return sizes.length ? Math.ceil(Math.max(...sizes) * 1.2 * 2 + 20 + 32) : 0;
}

function TextLayer({ clip, bottomReserve }: { clip: TextClip; bottomReserve: number }) {
  const { width, height } = useVideoConfig();
  const format = Object.values(FORMATS).find((f) => f.width === width && f.height === height);
  const safe = format?.safe ?? { top: 80, bottom: 80, left: 80, right: 80 };
  const justify = { top: "flex-start", center: "center", bottom: "flex-end" }[clip.position];
  const color = TEXT_COLORS[clip.color];
  // Nunca texto blanco sobre verde: la caja es oscura salvo para texto "ink".
  const boxColor = clip.color === "ink" ? brand.green : "rgba(13, 14, 15, 0.86)";
  const content =
    clip.animation === "arrive" ? (
      <ArrivingText size={clip.size_px} weight={clip.weight} color={color}>
        {clip.text}
      </ArrivingText>
    ) : (
      <div
        style={{
          fontFamily: BRAND_FONT_STACK,
          fontWeight: clip.weight,
          fontSize: clip.size_px,
          lineHeight: 1.05,
          letterSpacing: "-0.02em",
          color,
        }}
      >
        {clip.text}
      </div>
    );
  return (
    <AbsoluteFill
      style={{
        padding: `${safe.top}px ${safe.right}px ${safe.bottom + (clip.position === "bottom" ? bottomReserve : 0)}px ${safe.left}px`,
        display: "flex",
        flexDirection: "column",
        justifyContent: justify,
        alignItems: clip.align === "center" ? "center" : "flex-start",
        textAlign: clip.align,
      }}
    >
      <div style={clip.box ? { backgroundColor: boxColor, padding: "18px 26px", borderRadius: 6 } : undefined}>
        {content}
      </div>
    </AbsoluteFill>
  );
}

function SubtitleLayer({ cues, size }: { cues: Array<{ start_frame: number; end_frame: number; text: string }>; size: number }) {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const format = Object.values(FORMATS).find((f) => f.width === width && f.height === height);
  const safe = format?.safe ?? { top: 80, bottom: 120, left: 80, right: 80 };
  const cue = cues.find((c) => frame >= c.start_frame && frame < c.end_frame);
  if (!cue) return null;
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        padding: `0 ${safe.right}px ${safe.bottom}px ${safe.left}px`,
      }}
    >
      <div
        style={{
          fontFamily: BRAND_FONT_STACK,
          fontWeight: 800,
          fontSize: size,
          lineHeight: 1.2,
          color: neutralsDark.text,
          backgroundColor: "rgba(13, 14, 15, 0.86)",
          padding: "10px 20px",
          borderRadius: 6,
          textAlign: "center",
        }}
      >
        {cue.text}
      </div>
    </AbsoluteFill>
  );
}

function BrandLayer({ clip, sources, bottomReserve }: { clip: BrandClip; sources: ResolvedSources; bottomReserve: number }) {
  const { width, height } = useVideoConfig();
  const source = sources[brandKey(clip.brand_asset_id)];
  if (!source) throw new Error(`Recurso de marca no resuelto: ${clip.brand_asset_id}`);
  const format = Object.values(FORMATS).find((f) => f.width === width && f.height === height);
  const safe = format?.safe ?? { top: 80, bottom: 80, left: 80, right: 80 };
  const pos: Record<BrandClip["corner"], CSSProperties> = {
    top_left: { top: safe.top, left: safe.left },
    top_right: { top: safe.top, right: safe.right },
    bottom_left: { bottom: safe.bottom + bottomReserve, left: safe.left },
    bottom_right: { bottom: safe.bottom + bottomReserve, right: safe.right },
    center: { top: "50%", left: "50%", transform: "translate(-50%, -50%)" },
  };
  // Ancho fijo y alto automático: el logo conserva su proporción.
  return <Img src={source.src} style={{ position: "absolute", width: clip.width_px, height: "auto", ...pos[clip.corner] }} />;
}

function EvaluationWatermark() {
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 48 }}>
      <div
        style={{
          fontFamily: MONO_FONT_STACK,
          fontWeight: 600,
          fontSize: 30,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: onGreen,
          backgroundColor: brand.green,
          padding: "8px 18px",
        }}
      >
        Evaluación técnica · no publicar
      </div>
    </AbsoluteFill>
  );
}

export function TimelineComposition({ timeline, sources, evaluation }: TimelineProps) {
  ensureBrandFonts();
  const t = timelineSchema.parse(timeline);
  const fps = t.output.fps;
  const band = subtitleBand(t);
  return (
    <AbsoluteFill style={{ backgroundColor: neutralsDark.background }}>
      {t.tracks.map((track) => {
        switch (track.kind) {
          case "video":
            return track.clips.map((clip) => {
              const length = videoClipFrames(clip, fps);
              return (
                <Sequence key={`${track.id}-${clip.id}`} from={clip.at_frame} durationInFrames={length}>
                  <VideoLayer clip={clip} sources={sources} length={length} />
                </Sequence>
              );
            });
          case "text":
            return track.clips.map((clip) => (
              <Sequence key={`${track.id}-${clip.id}`} from={clip.at_frame} durationInFrames={clip.duration_frames}>
                <TextLayer clip={clip} bottomReserve={band} />
              </Sequence>
            ));
          case "subtitles":
            return <SubtitleLayer key={track.id} cues={track.cues} size={track.size_px} />;
          case "brand":
            return track.clips.map((clip) => (
              <Sequence key={`${track.id}-${clip.id}`} from={clip.at_frame} durationInFrames={clip.duration_frames}>
                <BrandLayer clip={clip} sources={sources} bottomReserve={band} />
              </Sequence>
            ));
          case "audio":
            return track.clips.map((clip) => {
              const key = clip.asset_id ? assetKey(clip.asset_id) : brandKey(clip.brand_asset_id ?? "");
              const source = sources[key];
              if (!source) throw new Error(`Audio no resuelto: ${key}`);
              return (
                <Sequence key={`${track.id}-${clip.id}`} from={clip.at_frame} durationInFrames={clip.duration_frames}>
                  <Audio src={source.src} trimBefore={Math.round(clip.source_in_s * fps)} volume={clip.volume} />
                </Sequence>
              );
            });
          default:
            return null;
        }
      })}
      {evaluation ? <EvaluationWatermark /> : null}
    </AbsoluteFill>
  );
}
