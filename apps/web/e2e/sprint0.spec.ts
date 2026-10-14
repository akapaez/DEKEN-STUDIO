/**
 * S0-12: recorrido de Sprint 0 con servicios reales.
 *
 * Login → Dashboard con estado real → tema claro/oscuro → alta de usuario → registro de
 * worker (token mostrado una vez) → worker real conectado → autotest de render con
 * FFmpeg → MP4 verificado y descargado → comprobación con ffprobe → permisos de un
 * usuario no administrador → logout.
 */
import { type ChildProcess, execFileSync, spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "";
const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";
const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const RUN = Date.now().toString(36);

test.describe.configure({ mode: "serial" });

let worker: ChildProcess | null = null;
const editor = { email: `editor-${RUN}@deken.test`, password: "Editor-E2E-Segura-2026" };

async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("heading", { name: /^Hola,/ })).toBeVisible();
}

test.beforeAll(() => {
  expect(ADMIN_EMAIL, "E2E_ADMIN_EMAIL").not.toBe("");
  expect(ADMIN_PASSWORD, "E2E_ADMIN_PASSWORD").not.toBe("");
});

test.afterAll(() => {
  worker?.kill("SIGTERM");
});

test("sin sesión, la aplicación redirige al login", async ({ page }) => {
  await page.goto("/configuracion");
  await expect(page).toHaveURL(/\/login\?next=%2Fconfiguracion/);
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
});

test("credenciales incorrectas muestran un error genérico", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByLabel("Contraseña").fill("incorrecta-123456");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Email o contraseña incorrectos" })).toBeVisible();
});

test("dashboard con estado real y navegación honesta", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await expect(page.getByText("Base de datos", { exact: true })).toBeVisible();
  await expect(page.getByText("Operativo").first()).toBeVisible();
  await expect(page.getByText("No configurado")).toBeVisible(); // IA sin clave: se dice claramente
  const nav = page.getByRole("navigation", { name: "Secciones" });
  await expect(nav.getByRole("link")).toHaveCount(2); // Dashboard y Configuración
  await expect(nav.getByText("Biblioteca")).toBeVisible();
  await expect(nav.locator('[aria-disabled="true"]')).toHaveCount(8);
});

test("tema claro y oscuro", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  const html = page.locator("html");
  const toggle = page.getByRole("button", { name: /Tema del sistema/ });
  await toggle.click();
  await expect(html).toHaveAttribute("data-theme", "light");
  const lightBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await page.getByRole("button", { name: /Tema claro/ }).click();
  await expect(html).toHaveAttribute("data-theme", "dark");
  const darkBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(lightBg).toBe("rgb(245, 246, 247)");
  expect(darkBg).toBe("rgb(13, 14, 15)");
  await page.reload();
  await expect(html).toHaveAttribute("data-theme", "dark"); // preferencia persistida
  await page.getByRole("button", { name: /Tema oscuro/ }).click();
});

test("alta de usuario editor", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.goto("/configuracion?tab=usuarios");
  await page.getByLabel("Nombre completo").fill("Editora E2E");
  await page.getByLabel("Email").fill(editor.email);
  await page.getByLabel("Rol", { exact: true }).selectOption("editor");
  await page.getByLabel("Contraseña inicial").fill(editor.password);
  await page.getByRole("button", { name: "Crear usuario" }).click();
  await expect(page.getByText("Usuario creado")).toBeVisible();
  await expect(page.getByRole("cell", { name: editor.email })).toBeVisible();
});

test("worker real + autotest de render verificado y descargado", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.goto("/configuracion?tab=workers");
  await page.getByLabel("Nombre del equipo").fill(`e2e-${RUN}`);
  await page.getByRole("button", { name: "Registrar worker" }).click();
  const token = (await page.getByTestId("worker-token").textContent())?.trim() ?? "";
  expect(token).toMatch(/^dkw_/);

  worker = spawn("uv", ["run", "deken-worker", "run"], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      DEKEN_API_URL: API_URL,
      DEKEN_WORKER_TOKEN: token,
      DEKEN_WORKER_QUEUES: "render",
      DEKEN_WORK_DIR: mkdtempSync(join(tmpdir(), "deken-e2e-worker-")),
      DEKEN_CLAIM_WAIT_SECONDS: "5",
    },
    stdio: "inherit",
  });

  await expect(async () => {
    await page.reload();
    await expect(page.getByRole("row", { name: new RegExp(`e2e-${RUN}`) }).getByText("En línea")).toBeVisible({
      timeout: 2_000,
    });
  }).toPass({ timeout: 60_000 });

  await page.goto("/configuracion?tab=sistema");
  await page.getByRole("button", { name: "Ejecutar autotest" }).click();
  await expect(page.getByText("Verificado en el servidor con ffprobe")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByText("Completado").first()).toBeVisible();
  await expect(page.getByText("h264 · 1080×1920 · yuv420p")).toBeVisible();
  await expect(page.getByText("90 a 30 fps")).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Descargar MP4" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^deken-autotest-sintetico-.*\.mp4$/);
  const file = join(mkdtempSync(join(tmpdir(), "deken-e2e-dl-")), "autotest.mp4");
  await download.saveAs(file);

  const probe = JSON.parse(
    execFileSync("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", file]).toString(),
  ) as { streams: Array<Record<string, string | number>>; format: { duration: string } };
  const video = probe.streams.find((s) => s.codec_type === "video")!;
  const audio = probe.streams.find((s) => s.codec_type === "audio")!;
  expect([video.codec_name, video.width, video.height, video.avg_frame_rate]).toEqual(["h264", 1080, 1920, "30/1"]);
  expect(audio.codec_name).toBe("aac");
  expect(Math.abs(Number(probe.format.duration) - 3)).toBeLessThan(0.05);
});

test("un editor no ve la administración ni puede lanzar el autotest", async ({ page }) => {
  await login(page, editor.email, editor.password);
  await page.goto("/configuracion");
  const tabs = page.getByRole("navigation", { name: "Apartados de configuración" });
  await expect(tabs.getByRole("link", { name: "Trabajos" })).toBeVisible();
  await expect(tabs.getByRole("link", { name: "Usuarios" })).toHaveCount(0);
  await expect(tabs.getByRole("link", { name: "Auditoría" })).toHaveCount(0);
  await expect(page.getByText("Solo los administradores pueden lanzar el autotest.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Ejecutar autotest" })).toHaveCount(0);
});

test("la auditoría registra el recorrido y el logout cierra la sesión", async ({ page }) => {
  await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await page.goto("/configuracion?tab=auditoria");
  for (const action of ["auth.login", "user.create", "worker.register", "job.create", "file.download_url"]) {
    await expect(page.getByRole("cell", { name: action, exact: true }).first()).toBeVisible();
  }
  await page.getByRole("button", { name: "Salir" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
});
