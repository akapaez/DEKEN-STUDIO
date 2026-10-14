// Genera el JSON Schema de la línea de tiempo desde el esquema zod (fuente única) y lo
// copia al paquete Python compartido. Con --check falla si las copias no están al día.
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { build } from "esbuild";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../..");
const targets = [
  join(root, "packages/video-compositions/schema/timeline.schema.json"),
  join(root, "packages/shared/python/src/deken_shared/schemas/timeline.schema.json"),
];

const outFile = join(mkdtempSync(join(tmpdir(), "deken-schema-")), "entry.mjs");
await build({
  entryPoints: [join(here, "schema-entry.ts")],
  bundle: true,
  platform: "node",
  format: "esm",
  outfile: outFile,
  logLevel: "warning",
});
const { timelineJsonSchema } = await import(pathToFileURL(outFile).href);
const json = `${JSON.stringify(timelineJsonSchema(), null, 2)}\n`;

if (process.argv.includes("--check")) {
  const stale = targets.filter((t) => {
    try {
      return readFileSync(t, "utf-8") !== json;
    } catch {
      return true;
    }
  });
  if (stale.length) {
    console.error(`JSON Schema de la timeline desactualizado: ${stale.join(", ")}. Ejecuta pnpm generate:schema`);
    process.exit(1);
  }
  console.log("JSON Schema de la timeline al día.");
} else {
  for (const t of targets) {
    mkdirSync(dirname(t), { recursive: true });
    writeFileSync(t, json);
  }
  console.log(`Escrito en:\n${targets.join("\n")}`);
}
