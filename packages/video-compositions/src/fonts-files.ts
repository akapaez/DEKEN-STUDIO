/**
 * Ficheros de las tipografías de marca para el bundle de render (worker y Remotion Studio).
 * Solo lo importa `entry.ts`: la web usa sus propias fuentes (fontsource) y no lo necesita.
 */
import montserratUrl from "@fontsource-variable/montserrat/files/montserrat-latin-wght-normal.woff2";
import plexMonoUrl from "@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-600-normal.woff2";

import { BRAND_FONT, MONO_FONT, registerFontLoader } from "./fonts";

registerFontLoader(async () => {
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
});
