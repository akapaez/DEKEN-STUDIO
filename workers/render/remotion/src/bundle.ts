#!/usr/bin/env node
/**
 * Genera el bundle web de las composiciones (una vez por versión; se reutiliza en cada
 * render). Uso: node dist/bundle.js <directorio-salida>
 */
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";

import { bundle } from "@remotion/bundler";

const require = createRequire(import.meta.url);
const pkgDir = dirname(require.resolve("@deken/video-compositions/package.json"));
const outDir = resolve(process.argv[2] ?? "dist/bundle");

const started = Date.now();
const serveUrl = await bundle({
  entryPoint: join(pkgDir, "src/entry.ts"),
  outDir,
  enableCaching: false,
});
console.log(JSON.stringify({ event: "bundled", serve_url: serveUrl, ms: Date.now() - started }));
