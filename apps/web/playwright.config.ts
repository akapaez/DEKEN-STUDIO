import { defineConfig, devices } from "@playwright/test";

/**
 * E2E contra servicios reales (API, web, worker, PostgreSQL, Redis, S3).
 * Se ejecuta con infra/scripts/e2e.sh, que prepara una base de datos temporal.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "es-ES",
  },
  // E2E_BROWSER_CHANNEL=chrome usa Google Chrome instalado (con H.264/AAC para reproducir
  // los proxys); sin ella, el Chromium de Playwright.
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        ...(process.env.E2E_BROWSER_CHANNEL ? { channel: process.env.E2E_BROWSER_CHANNEL } : {}),
      },
    },
  ],
});
