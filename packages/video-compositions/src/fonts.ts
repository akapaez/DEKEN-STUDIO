/**
 * Tipografías de marca en las composiciones.
 *
 * Las familias se nombran con una pila: primero la fuente que carga el bundle de render
 * (`DekenMontserrat`, ver `fonts-files.ts`) y después la que ya tiene la web
 * ("Montserrat Variable", vía fontsource). Así el Player de la web y el render del worker
 * usan la MISMA composición sin que la web importe ficheros de fuentes.
 *
 * Si una fuente no carga, Remotion no da error: cae a la fuente por defecto. Por eso el
 * cargador registrado comprueba `document.fonts.check` y cancela el render si falla
 * (regla de la guía de marca: "¿las fuentes han cargado de verdad?").
 */
import { cancelRender, continueRender, delayRender } from "remotion";

export const BRAND_FONT = "DekenMontserrat";
export const MONO_FONT = "DekenPlexMono";
export const BRAND_FONT_STACK = `${BRAND_FONT}, "Montserrat Variable", Montserrat, sans-serif`;
export const MONO_FONT_STACK = `${MONO_FONT}, "IBM Plex Mono", ui-monospace, monospace`;

type FontLoader = () => Promise<void>;

let loader: FontLoader | null = null;
let loading: Promise<void> | null = null;

/** El bundle de render registra aquí la carga estricta de los ficheros de fuentes. */
export function registerFontLoader(next: FontLoader): void {
  loader = next;
}

/** Bloquea el render hasta que las fuentes de marca estén cargadas (una vez por página). */
export function ensureBrandFonts(): void {
  if (typeof document === "undefined" || loading || !loader) return;
  const handle = delayRender("Cargando tipografías de marca");
  loading = loader().then(
    () => continueRender(handle),
    (err: unknown) => cancelRender(err instanceof Error ? err : new Error(String(err))),
  );
}
