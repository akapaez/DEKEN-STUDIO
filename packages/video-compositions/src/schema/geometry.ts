/**
 * Geometría de reencuadre. Regla: NUNCA deformar. La imagen se escala con el mismo
 * factor en ambos ejes; el reencuadre solo elige qué parte del original se ve.
 */
import type { Reframe } from "./timeline";

export interface Size {
  width: number;
  height: number;
}

export interface Placement {
  /** Tamaño al que se dibuja el original (mismo factor en X e Y). */
  width: number;
  height: number;
  /** Desplazamiento del original respecto a la esquina del fotograma. */
  left: number;
  top: number;
  scale: number;
}

export const aspect = (s: Size) => s.width / s.height;

/** Reencuadre centrado que llena la salida sin deformar (equivale a object-fit: cover). */
export function centeredCoverReframe(source: Size, output: Size): Reframe {
  const sa = aspect(source);
  const oa = aspect(output);
  if (sa > oa) {
    const w = oa / sa;
    return { x: (1 - w) / 2, y: 0, w, h: 1 };
  }
  const h = sa / oa;
  return { x: 0, y: (1 - h) / 2, w: 1, h };
}

/** Comprueba que el rectángulo tiene la relación de aspecto de la salida (±1 %). */
export function reframeMatchesOutput(r: Reframe, source: Size, output: Size, tolerance = 0.01): boolean {
  const rectAspect = (r.w * source.width) / (r.h * source.height);
  return Math.abs(rectAspect / aspect(output) - 1) <= tolerance;
}

/** Colocación del original para que `r` llene exactamente la salida. */
export function placeReframe(r: Reframe, source: Size, output: Size): Placement {
  const scale = output.width / (r.w * source.width);
  return {
    scale,
    width: source.width * scale,
    height: source.height * scale,
    left: -r.x * source.width * scale,
    top: -r.y * source.height * scale,
  };
}

/** Imagen completa dentro de la salida (letterbox/pillarbox), sin deformar. */
export function placeContain(source: Size, output: Size): Placement {
  const scale = Math.min(output.width / source.width, output.height / source.height);
  const width = source.width * scale;
  const height = source.height * scale;
  return { scale, width, height, left: (output.width - width) / 2, top: (output.height - height) / 2 };
}
