#!/usr/bin/env node
/**
 * Instala Chrome Headless Shell (la versión que fija @remotion/renderer) dentro de este
 * paquete: node_modules/.remotion/. El worker lo encuentra ahí; así ningún render lo
 * descarga en el directorio de un trabajo. Uso: pnpm --filter @deken/remotion-renderer browser
 */
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { ensureBrowser } from "@remotion/renderer";

process.chdir(resolve(dirname(fileURLToPath(import.meta.url)), ".."));
const status = await ensureBrowser();
console.log(JSON.stringify({ event: "browser", ...status }));
