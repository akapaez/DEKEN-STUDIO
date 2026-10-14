/**
 * Paleta de Grupo Deken.
 *
 * Fuente: valores medidos sobre los logos reales (skill de marca `estilo-de-marca`).
 * Deken tiene exactamente DOS colores de marca. El resto son neutros derivados del
 * gris Deken (mismo tono 204° y saturación 8,2 %, solo cambia la luminosidad).
 *
 * Reglas:
 * - El verde es el ÚNICO acento. Se usa plano: nunca degradado, nunca resplandor.
 * - Texto blanco sobre verde está PROHIBIDO (2,42:1). Sobre verde, texto `ink`.
 * - Los colores de estado (`danger`, `warning`) son funcionales de interfaz, no de
 *   marca: siempre acompañados de icono o texto, nunca como único indicador.
 */

export const brand = {
  /** Verde Deken. Acento único. */
  green: "#76B82A",
  /** Gris Deken. Bordes, separadores, superficies. */
  gray: "#383E42",
} as const;

/** Neutros medidos en la guía de marca (tema oscuro, el nativo de la marca). */
export const neutralsDark = {
  background: "#0D0E0F",
  surface: "#16191A",
  surfaceRaised: "#1A1D1E",
  border: brand.gray,
  text: "#FFFFFF",
  textSecondary: "#A1AAAF",
  label: "#7B878F",
} as const;

/** Neutros del tema claro: mismo tono y saturación del gris Deken, luminosidad invertida. */
export const neutralsLight = {
  background: "#F5F6F7",
  surface: "#FFFFFF",
  surfaceRaised: "#ECEEEF",
  border: "#CED3D6",
  text: "#0D0E0F",
  textSecondary: brand.gray,
  label: "#59636A",
} as const;

/** Texto sobre fondo verde (7,97:1). */
export const onGreen = "#0D0E0F";

/** Colores funcionales de estado (solo interfaz). */
export const status = {
  dangerDark: "#FF6B6B",
  dangerLight: "#B42318",
  warningDark: "#F5B841",
  warningLight: "#8A5A00",
} as const;

export const typography = {
  /** Tipografía de marca: titulares, cifras y texto. Sin cursiva. */
  brand: "Montserrat Variable, Montserrat, system-ui, sans-serif",
  /** Funcional para datos técnicos: IDs, hashes, códecs, etiquetas. */
  mono: "IBM Plex Mono, ui-monospace, monospace",
  headingWeight: 800,
  headingTracking: "-0.02em",
  labelTracking: "0.16em",
} as const;

/** Formato de exportación V1 y mínimos de legibilidad en vídeo vertical. */
export const video = {
  width: 1080,
  height: 1920,
  fps: 30,
  minTextPx: 30,
  headlinePx: { min: 90, max: 160 },
  /** El logo no aparece en los primeros segundos (parece un anuncio). */
  logoNotBeforeSeconds: 3,
} as const;
