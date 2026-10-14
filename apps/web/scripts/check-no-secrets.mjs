// S0-13: comprueba que ningún secreto del entorno aparece en el build de la web.
// Uso: node scripts/check-no-secrets.mjs [ruta/.env ...]  (por defecto, ../../infra/.env)
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const buildDir = resolve(here, "../.next");
const envFiles = process.argv.slice(2).length
  ? process.argv.slice(2)
  : [resolve(here, "../../../infra/.env")];
const SECRET_KEY = /(SECRET|PASSWORD|ACCESS_KEY|TOKEN|API_KEY)/;

const secrets = new Map();
for (const file of envFiles) {
  if (!existsSync(file)) continue;
  for (const line of readFileSync(file, "utf-8").split("\n")) {
    const match = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
    if (match && SECRET_KEY.test(match[1]) && match[2].length >= 8) secrets.set(match[1], match[2]);
  }
}
for (const [key, value] of Object.entries(process.env)) {
  if (key.startsWith("DEKEN_") && SECRET_KEY.test(key) && value && value.length >= 8) secrets.set(key, value);
}
if (secrets.size === 0) {
  console.error("No hay secretos que comprobar (¿falta infra/.env?)");
  process.exit(2);
}
if (!existsSync(buildDir)) {
  console.error("No existe .next: ejecuta antes `pnpm build`");
  process.exit(2);
}

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    if (name === "cache") continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* walk(path);
    else yield path;
  }
}

let scanned = 0;
const leaks = [];
for (const file of walk(buildDir)) {
  const content = readFileSync(file);
  scanned += 1;
  for (const [key, value] of secrets) {
    if (content.includes(value)) leaks.push(`${key} en ${file}`);
  }
}
if (leaks.length) {
  console.error(`¡Secretos encontrados en el build!\n${leaks.join("\n")}`);
  process.exit(1);
}
console.log(`OK: ${secrets.size} secretos comprobados en ${scanned} ficheros del build; ninguno aparece.`);
