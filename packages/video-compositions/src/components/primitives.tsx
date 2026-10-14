import { brand, neutralsDark, onGreen } from "@deken/brand";
import type { CSSProperties, ReactNode } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

import { BRAND_FONT_STACK, MONO_FONT_STACK } from "../fonts";
import { arrival, arriveFrames, cameraPush } from "../motion";

/** Fondo plano de marca con un empuje de cámara suave (≤ 6 %). */
export function BrandBackground({
  color = brand.gray,
  push = 0.03,
  children,
}: {
  color?: string;
  push?: number;
  children?: ReactNode;
}) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: color }}>
      <AbsoluteFill style={{ transform: `scale(${cameraPush(frame, durationInFrames, push)})` }}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

/** Texto que "llega": de desenfocado y desplazado a nítido, sin rebotes. */
export function ArrivingText({
  children,
  start = 0,
  size,
  weight = 900,
  color = neutralsDark.text,
  style,
}: {
  children: ReactNode;
  start?: number;
  size: number;
  weight?: 800 | 900 | 700 | 600;
  color?: string;
  style?: CSSProperties;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = arrival(frame, start, arriveFrames(fps));
  return (
    <div
      style={{
        fontFamily: BRAND_FONT_STACK,
        fontWeight: weight,
        fontSize: size,
        lineHeight: 1,
        letterSpacing: "-0.02em",
        color,
        opacity: p,
        filter: `blur(${(1 - p) * 18}px)`,
        transform: `translateY(${(1 - p) * 40}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** Línea gráfica verde plana que crece (nunca degradado ni resplandor). */
export function GreenRule({
  start = 0,
  width,
  thickness = 12,
}: {
  start?: number;
  width: number;
  thickness?: number;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = arrival(frame, start, arriveFrames(fps, 0.8));
  return <div style={{ width: width * p, height: thickness, backgroundColor: brand.green }} />;
}

/** Etiqueta técnica en mayúsculas (IBM Plex Mono, tracking 0,16 em). */
export function Label({ children, start = 0, size = 32 }: { children: ReactNode; start?: number; size?: number }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = arrival(frame, start, arriveFrames(fps, 0.5));
  return (
    <div
      style={{
        fontFamily: MONO_FONT_STACK,
        fontWeight: 600,
        fontSize: Math.max(30, size),
        letterSpacing: "0.16em",
        textTransform: "uppercase",
        color: neutralsDark.textSecondary,
        opacity: p,
      }}
    >
      {children}
    </div>
  );
}

/** Barrido plano en verde que cubre y descubre la imagen (transición sencilla). */
export function GreenWipe({ start, duration }: { start: number; duration: number }) {
  const frame = useCurrentFrame();
  const half = duration / 2;
  const cover = interpolate(frame, [start, start + half], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const reveal = interpolate(frame, [start + half, start + duration], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (frame < start || frame > start + duration) return null;
  return (
    <AbsoluteFill
      style={{
        backgroundColor: brand.green,
        clipPath: `inset(0 ${100 - cover}% 0 ${reveal}%)`,
        color: onGreen,
      }}
    />
  );
}

/** Contenedor con márgenes de zona segura (en píxeles de la salida). */
export function SafeArea({
  top,
  bottom,
  left,
  right,
  children,
  justify = "center",
}: {
  top: number;
  bottom: number;
  left: number;
  right: number;
  children: ReactNode;
  justify?: CSSProperties["justifyContent"];
}) {
  return (
    <AbsoluteFill
      style={{
        padding: `${top}px ${right}px ${bottom}px ${left}px`,
        display: "flex",
        flexDirection: "column",
        justifyContent: justify,
        gap: 36,
      }}
    >
      {children}
    </AbsoluteFill>
  );
}
