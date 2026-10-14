/**
 * Sprint 1 (S1-01 a S1-06) + Remotion, con servicios reales y un worker real.
 *
 * Biblioteca: subida multiparte desde el navegador → validación en servidor → ingesta
 * (póster, tira, proxy, forma de onda) → ficha con reproductor → catalogación y filtros →
 * derechos de imagen → descarga del original idéntico. Fichero falso rechazado.
 * Marca: logos analizados (tinta medida, proporción, fondo). Remotion: previsualización con
 * el Player y render de evaluación verificado con ffprobe.
 *
 * Todo el material es SINTÉTICO (generado aquí con FFmpeg); ninguno es de DEKEN.
 */
import { type ChildProcess, execFileSync, spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "";
const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";
const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const RUN = Date.now().toString(36);
const WORK = mkdtempSync(join(tmpdir(), "deken-e2e-s1-"));
const TITLE = `Corte de perfiles sintético ${RUN}`;
const viewer = { email: `consulta-${RUN}@deken.test`, password: "Consulta-E2E-Segura-2026" };

test.describe.configure({ mode: "serial" });

let worker: ChildProcess | null = null;
let videoPath = "";

const sha256 = (path: string) => createHash("sha256").update(readFileSync(path)).digest("hex");

function ffmpeg(args: string[]) {
  execFileSync("ffmpeg", ["-v", "error", "-y", ...args]);
}

async function login(page: Page, email = ADMIN_EMAIL, password = ADMIN_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("heading", { name: /^Hola,/ })).toBeVisible();
}

test.beforeAll(() => {
  expect(ADMIN_EMAIL, "E2E_ADMIN_EMAIL").not.toBe("");
  videoPath = join(WORK, "corte-perfiles.mp4");
  ffmpeg([
    "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=3",
    "-f", "lavfi", "-i", "sine=frequency=440:duration=3:sample_rate=48000",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
    "-metadata", "comment=SINTETICO - prueba E2E, no es material de DEKEN", videoPath,
  ]); // prettier-ignore
  writeFileSync(join(WORK, "no-es-video.mp4"), "Esto es texto con extensión .mp4\n".repeat(500));
  ffmpeg(["-f", "lavfi", "-i", "color=c=0x76B82A:s=520x100,format=rgba", "-frames:v", "1", join(WORK, "DEKEN-VERDE.png")]);
  ffmpeg(["-f", "lavfi", "-i", "color=c=0x383E42:s=2200x200,format=rgba", "-frames:v", "1", join(WORK, "GRUPO-DEKEN-HORIZONTAL-BLANCO.png")]);
});

test.afterAll(() => {
  worker?.kill("SIGTERM");
});

test("worker de análisis y render conectado", async ({ page }) => {
  await login(page);
  await page.goto("/configuracion?tab=workers");
  await page.getByLabel("Nombre del equipo").fill(`e2e-s1-${RUN}`);
  await page.getByRole("button", { name: "Registrar worker" }).click();
  const token = (await page.getByTestId("worker-token").textContent())?.trim() ?? "";
  expect(token).toMatch(/^dkw_/);
  worker = spawn("uv", ["run", "deken-worker", "run"], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      DEKEN_API_URL: API_URL,
      DEKEN_WORKER_TOKEN: token,
      DEKEN_WORKER_QUEUES: "analysis,render",
      DEKEN_WORK_DIR: mkdtempSync(join(tmpdir(), "deken-e2e-s1-worker-")),
      DEKEN_CLAIM_WAIT_SECONDS: "5",
    },
    stdio: "inherit",
  });
  await expect(async () => {
    await page.reload();
    await expect(page.getByRole("row", { name: new RegExp(`e2e-s1-${RUN}`) }).getByText("En línea")).toBeVisible({
      timeout: 2_000,
    });
  }).toPass({ timeout: 60_000 });
});

test("S1-01/S1-03/S1-04: subida desde el navegador, ingesta y ficha con reproductor", async ({ page }) => {
  await login(page);
  await page.goto("/biblioteca");
  await expect(page.getByRole("heading", { name: "Grabaciones de DEKEN" })).toBeVisible();
  await page.getByTestId("media-file-input").setInputFiles([videoPath, join(WORK, "no-es-video.mp4")]);

  const uploads = page.getByRole("list", { name: "Subidas" });
  const fake = uploads.getByRole("listitem").filter({ hasText: "no-es-video.mp4" });
  await expect(fake.getByText("Rechazada")).toBeVisible({ timeout: 60_000 });
  const real = uploads.getByRole("listitem").filter({ hasText: "corte-perfiles.mp4" });
  await expect(real.getByText(/Procesando|Lista/)).toBeVisible({ timeout: 60_000 });
  await real.getByRole("link", { name: "Ver ficha" }).click();

  await expect(page.getByText("Lista", { exact: true })).toBeVisible({ timeout: 120_000 });
  await expect(page.getByText("1080×1920 · Vertical")).toBeVisible();
  const player = page.locator("video[aria-label^='Proxy de ']");
  await expect(player).toBeVisible();
  // El proxy servido es un MP4 H.264 540×960 válido y completo.
  const proxyUrl = (await player.getAttribute("src")) ?? "";
  const proxy = await page.request.get(proxyUrl);
  expect(proxy.status()).toBe(200);
  const proxyFile = join(WORK, "proxy.mp4");
  writeFileSync(proxyFile, await proxy.body());
  const proxyProbe = JSON.parse(
    execFileSync("ffprobe", ["-v", "error", "-show_streams", "-of", "json", proxyFile]).toString(),
  ) as { streams: Array<Record<string, string | number>> };
  const proxyVideo = proxyProbe.streams.find((s) => s.codec_type === "video")!;
  expect([proxyVideo.codec_name, proxyVideo.width, proxyVideo.height]).toEqual(["h264", 540, 960]);
  // Reproducción real en el navegador (CSP media-src). El Chromium de Playwright no trae
  // H.264; en CI se usa Google Chrome (E2E_BROWSER_CHANNEL=chrome), que sí lo decodifica.
  const h264 = await page.evaluate(() => document.createElement("video").canPlayType('video/mp4; codecs="avc1.64001f"'));
  if (h264) {
    await expect
      .poll(() => player.evaluate((v: HTMLVideoElement) => v.readyState), { timeout: 30_000 })
      .toBeGreaterThanOrEqual(1);
    expect(await player.evaluate((v: HTMLVideoElement) => [v.videoWidth, v.videoHeight])).toEqual([540, 960]);
  } else {
    test.info().annotations.push({ type: "nota", description: "Navegador sin H.264: reproducción no comprobada" });
  }
  await expect(page.getByRole("slider", { name: /Forma de onda/ })).toBeVisible();

  // Catalogación.
  await page.getByRole("textbox", { name: "Título" }).fill(TITLE);
  await page.getByRole("textbox", { name: "Etiquetas" }).fill("Corte, perfiles, línea 2");
  await page.getByRole("button", { name: "Guardar catalogación" }).click();
  await expect(page.getByText("Catalogación guardada")).toBeVisible();

  // Derechos de imagen: conceder sin referencia es un error; con referencia, utilizable.
  await page.getByLabel("¿Aparecen personas?").selectOption("yes");
  await page.getByLabel("Consentimiento", { exact: true }).selectOption("granted");
  await page.getByRole("button", { name: "Guardar derechos" }).click();
  await expect(page.getByRole("alert").filter({ hasText: /referencia/i })).toBeVisible();
  await page.getByLabel("Referencia del consentimiento").fill(`RRHH-E2E-${RUN}`);
  await page.getByRole("button", { name: "Guardar derechos" }).click();
  await expect(page.getByText("Utilizable en piezas")).toBeVisible();

  // Original inmutable: lo descargado es idéntico byte a byte a lo subido.
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Descargar original" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("corte-perfiles.mp4");
  const saved = join(WORK, "descargado.mp4");
  await download.saveAs(saved);
  expect(sha256(saved)).toBe(sha256(videoPath));
});

test("S1-02: galería, búsqueda y filtro por etiqueta", async ({ page }) => {
  await login(page);
  await page.goto("/biblioteca");
  const grid = page.getByRole("list", { name: "Vídeos" });
  await expect(grid.getByRole("link", { name: `Abrir ${TITLE}` })).toBeVisible();
  await expect(grid.getByRole("link", { name: /Abrir no-es-video/ })).toBeVisible(); // rechazado, visible con su estado

  await page.getByLabel("Buscar en la biblioteca").fill(RUN);
  await expect(grid.getByRole("link")).toHaveCount(1);
  await page.getByLabel("Buscar en la biblioteca").fill("");

  await page.getByRole("group", { name: "Filtrar por etiqueta" }).getByRole("button", { name: /^corte/ }).click();
  await expect(grid.getByRole("link")).toHaveCount(1);
  await page.getByLabel("Estado").selectOption("rejected");
  await expect(page.getByText("Ningún vídeo coincide con los filtros")).toBeVisible();
});

test("S1-06: logos oficiales analizados en la sección de marca", async ({ page }) => {
  await login(page);
  await page.goto("/marca");
  await expect(page.getByRole("heading", { name: "Identidad visual oficial" })).toBeVisible();

  for (const file of ["DEKEN-VERDE.png", "GRUPO-DEKEN-HORIZONTAL-BLANCO.png"]) {
    await page.getByTestId("brand-file-input").setInputFiles(join(WORK, file));
    await page.getByRole("button", { name: "Subir y analizar" }).click();
    await expect(page.getByText(/analizado y disponible/)).toBeVisible();
  }
  const green = page.getByRole("listitem").filter({ hasText: "DEKEN-VERDE.png" });
  await expect(green.getByText("#76B82A")).toBeVisible();
  await expect(green.getByText("Fondo oscuro · uso indicado")).toBeVisible();
  await expect(green.getByText("DEKEN", { exact: true })).toBeVisible(); // familia por proporción 5,2
  const swapped = page.getByRole("listitem").filter({ hasText: "GRUPO-DEKEN-HORIZONTAL-BLANCO.png" });
  await expect(swapped.getByText("Color distinto al del nombre")).toBeVisible();
  await expect(swapped.getByText("Fondo claro · uso indicado")).toBeVisible();
});

test("Remotion: previsualización con Player y render de evaluación verificado", async ({ page }) => {
  await login(page);
  await page.goto("/configuracion?tab=sistema");
  await expect(page.getByText("Solo evaluación")).toBeVisible();
  await expect(page.getByText("Renders comerciales")).toBeVisible();
  await expect(page.getByText("deshabilitados")).toBeVisible();
  await page.getByLabel("Título", { exact: true }).fill("Prueba E2E");
  // La previsualización usa la misma composición: el texto aparece en el Player.
  await expect(page.getByText("Prueba E2E", { exact: true }).first()).toBeVisible({ timeout: 30_000 });

  await page.getByRole("button", { name: "Renderizar con Remotion" }).click();
  const job = page.getByRole("region", { name: "Evaluación de Remotion" });
  await expect(job.getByText(/no apto para uso comercial/)).toBeVisible({ timeout: 240_000 });
  await expect(job.getByText("h264 · 1080×1920 · yuv420p")).toBeVisible();
  await expect(job.getByText("150 a 30 fps")).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await job.getByRole("button", { name: "Descargar MP4" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^deken-evaluacion-remotion-.*\.mp4$/);
  const file = join(WORK, "remotion.mp4");
  await download.saveAs(file);
  const probe = JSON.parse(
    execFileSync("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", file]).toString(),
  ) as { streams: Array<Record<string, string | number>>; format: { duration: string } };
  const video = probe.streams.find((s) => s.codec_type === "video")!;
  expect([video.codec_name, video.width, video.height, video.avg_frame_rate]).toEqual(["h264", 1080, 1920, "30/1"]);
  expect(Math.abs(Number(probe.format.duration) - 5)).toBeLessThan(0.05);
});

test("un usuario de consulta ve la biblioteca pero no puede subir ni editar", async ({ page }) => {
  await login(page);
  await page.goto("/configuracion?tab=usuarios");
  await page.getByLabel("Nombre completo").fill("Consulta E2E");
  await page.getByLabel("Email").fill(viewer.email);
  await page.getByLabel("Rol", { exact: true }).selectOption("viewer");
  await page.getByLabel("Contraseña inicial").fill(viewer.password);
  await page.getByRole("button", { name: "Crear usuario" }).click();
  await expect(page.getByText("Usuario creado")).toBeVisible();
  await page.getByRole("button", { name: "Salir" }).click();

  await login(page, viewer.email, viewer.password);
  await page.goto("/biblioteca");
  await expect(page.getByRole("link", { name: `Abrir ${TITLE}` })).toBeVisible();
  await expect(page.getByRole("button", { name: "Elegir ficheros" })).toHaveCount(0);
  await page.getByRole("link", { name: `Abrir ${TITLE}` }).click();
  await expect(page.getByText("Solo revisión o administración pueden modificar los derechos de imagen.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Guardar catalogación" })).toHaveCount(0);
  await page.goto("/marca");
  await expect(page.getByRole("button", { name: "Subir y analizar" })).toHaveCount(0);
});
