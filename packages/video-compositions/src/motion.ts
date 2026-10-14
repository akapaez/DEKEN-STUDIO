/**
 * Ritmo de marca DEKEN (guía `estilo-de-marca`):
 * - Nada aparece: todo llega, de desenfocado a nítido, con cubic-bezier(0.16, 1, 0.3, 1)
 *   en 0,5–0,8 s.
 * - Sin sacudidas, flashes, rebotes ni golpes de escala. Empuje de cámara ≤ 6 %.
 * - Barrido de clip: 8 fotogramas de entrada y 7 de salida.
 * - Remate final: 1,2 s quieto antes del corte.
 */
import { Easing, interpolate } from "remotion";

export const ARRIVE = Easing.bezier(0.16, 1, 0.3, 1);
export const MAX_CAMERA_PUSH = 0.06;
export const CLIP_WIPE_IN_FRAMES = 8;
export const CLIP_WIPE_OUT_FRAMES = 7;
export const FINAL_HOLD_SECONDS = 1.2;

/** Duración de una llegada en fotogramas (0,5–0,8 s). */
export function arriveFrames(fps: number, seconds = 0.65): number {
  const clamped = Math.min(0.8, Math.max(0.5, seconds));
  return Math.round(clamped * fps);
}

/** Progreso 0→1 de una llegada que empieza en `start`. */
export function arrival(frame: number, start: number, duration: number): number {
  return interpolate(frame, [start, start + duration], [0, 1], {
    easing: ARRIVE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}

/** Empuje de cámara lineal y limitado al 6 %. */
export function cameraPush(frame: number, totalFrames: number, amount = 0.04): number {
  const safe = Math.min(MAX_CAMERA_PUSH, Math.max(0, amount));
  return 1 + interpolate(frame, [0, Math.max(1, totalFrames)], [0, safe], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}
