// Genera packages/shared/openapi/openapi.json (desde FastAPI) y src/api.d.ts.
// Con --check, falla si los ficheros versionados no están al día (uso en CI).
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../../../..");
const schemaPath = join(root, "packages/shared/openapi/openapi.json");
const typesPath = join(root, "packages/shared/ts/src/api.d.ts");
const check = process.argv.includes("--check");

const outDir = check ? mkdtempSync(join(tmpdir(), "deken-openapi-")) : dirname(schemaPath);
const newSchemaPath = check ? join(outDir, "openapi.json") : schemaPath;

execFileSync("uv", ["run", "deken-api", "export-openapi", "--out", newSchemaPath], {
  cwd: root,
  stdio: ["ignore", "ignore", "inherit"],
});

const schema = JSON.parse(readFileSync(newSchemaPath, "utf-8"));
const ast = await openapiTS(schema, { alphabetize: true });
const header =
  "/**\n * GENERADO desde la API (FastAPI → OpenAPI). No editar a mano.\n" +
  " * Regenerar: pnpm generate:api\n */\n\n";
const types = header + astToString(ast);

if (check) {
  const same =
    readFileSync(schemaPath, "utf-8") === readFileSync(newSchemaPath, "utf-8") &&
    readFileSync(typesPath, "utf-8") === types;
  if (!same) {
    console.error("OpenAPI o tipos TS desactualizados. Ejecuta: pnpm generate:api");
    process.exit(1);
  }
  console.log("OpenAPI y tipos TS al día.");
} else {
  writeFileSync(typesPath, types);
  console.log(`Tipos escritos en ${typesPath}`);
}
