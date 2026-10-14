/**
 * Formatos de salida y zonas seguras.
 *
 * Zonas seguras conservadoras para que la interfaz de cada red (botones, descripción,
 * barra de progreso) no tape textos ni logos. Valores en píxeles de la salida.
 */
export type FormatId = "vertical_9_16" | "horizontal_16_9" | "square_1_1";

export interface SafeInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface OutputFormat {
  id: FormatId;
  label: string;
  width: number;
  height: number;
  aspect: string;
  safe: SafeInsets;
}

export const FORMATS: Record<FormatId, OutputFormat> = {
  vertical_9_16: {
    id: "vertical_9_16",
    label: "Vertical 9:16 (Reels, Shorts, TikTok)",
    width: 1080,
    height: 1920,
    aspect: "9:16",
    // La descripción y los botones ocupan la parte baja y el lateral derecho.
    safe: { top: 220, bottom: 420, left: 72, right: 160 },
  },
  horizontal_16_9: {
    id: "horizontal_16_9",
    label: "Horizontal 16:9 (YouTube, LinkedIn, web)",
    width: 1920,
    height: 1080,
    aspect: "16:9",
    safe: { top: 96, bottom: 120, left: 120, right: 120 },
  },
  square_1_1: {
    id: "square_1_1",
    label: "Cuadrado 1:1 (feed)",
    width: 1080,
    height: 1080,
    aspect: "1:1",
    safe: { top: 80, bottom: 120, left: 80, right: 80 },
  },
};

export const OUTPUT_FPS = 30;

export function formatFor(width: number, height: number): OutputFormat | undefined {
  return Object.values(FORMATS).find((f) => f.width === width && f.height === height);
}
