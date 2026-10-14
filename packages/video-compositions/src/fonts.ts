/**
 * Carga de tipografías de marca dentro de la composición.
 *
 * Si una fuente no carga, Remotion no da error: cae a la fuente por defecto. Por eso
 * aquí se comprueba con `document.fonts.check` y se cancela el render si falla
 * (regla de la guía de marca: "¿las fuentes han cargado de verdad?").
 */
import montserratUrl from "@fontsource-variable/montserrat/files/montserrat-latin-wght-normal.woff2";
import plexMonoUrl from "@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-600-normal.woff2";
import { continueRender, delayRender, cancelRender } from "remotion";

export const BRAND_FONT = "DekenMontserrat";
export const MONO_FONT = "DekenPlexMono";

let loading: Promise<void> | null = null;

async function load(): Promise<void> {
  const faces = [
    new FontFace(BRAND_FONT, `url(${montserratUrl}) format("woff2")`, { weight: "100 900", style: "normal" }),
    new FontFace(MONO_FONT, `url(${plexMonoUrl}) format("woff2")`, { weight: "600", style: "normal" }),
  ];
  for (const face of faces) {
    await face.load();
    document.fonts.add(face);
  }
  await document.fonts.ready;
  for (const probe of [`900 64px ${BRAND_FONT}`, `600 32px ${MONO_FONT}`]) {
    if (!document.fonts.check(probe)) throw new Error(`La fuente no ha cargado: ${probe}`);
  }
}

/** Bloquea el render hasta que las fuentes de marca estén cargadas (una vez por página). */
export function ensureBrandFonts(): void {
  if (typeof document === "undefined" || loading) return;
  const handle = delayRender("Cargando tipografías de marca");
  loading = load().then(
    () => continueRender(handle),
    (err: unknown) => cancelRender(err instanceof Error ? err : new Error(String(err))),
  );
}
