import { describe, expect, it } from "vitest";

import { safeNext } from "@/app/login/LoginForm";
import { buildCsp } from "@/proxy";

import { ApiError, csrfMiddleware, errorMessage, readCookie, toApiError } from "./api";
import { formatBytes, formatDuration, formatRelative, jobTypeLabel, shortId } from "./format";
import { NAV_ITEMS, isActive } from "./nav";
import { nextThemePreference } from "./theme";

describe("navegación", () => {
  it("las diez secciones existen y solo las disponibles tienen ruta", () => {
    expect(NAV_ITEMS.map((i) => i.label)).toEqual([
      "Dashboard",
      "Director IA",
      "Biblioteca",
      "Productor audiovisual",
      "Editor",
      "Calendario",
      "Marca DEKEN",
      "Publicaciones",
      "Analítica y leads",
      "Configuración",
    ]);
    for (const item of NAV_ITEMS) {
      if (item.href === null) expect(item.availability).toMatch(/^(Sprint \d|V2)$/);
      else expect(item.availability).toBeUndefined();
    }
  });

  it("marca la sección activa", () => {
    const dashboard = NAV_ITEMS[0]!;
    const settings = NAV_ITEMS.at(-1)!;
    expect(isActive(dashboard, "/")).toBe(true);
    expect(isActive(dashboard, "/configuracion")).toBe(false);
    expect(isActive(settings, "/configuracion")).toBe(true);
  });
});

describe("cliente de API", () => {
  it("lee cookies", () => {
    expect(readCookie("deken_csrf", "a=1; deken_csrf=abc%3D; b=2")).toBe("abc=");
    expect(readCookie("nada", "a=1")).toBeNull();
  });

  it("añade el token CSRF solo en métodos no seguros", async () => {
    document.cookie = "deken_csrf=token-123";
    const onRequest = csrfMiddleware.onRequest!;
    const post = (await onRequest({ request: new Request("http://x/api", { method: "POST" }) } as never)) as Request;
    const get = (await onRequest({ request: new Request("http://x/api") } as never)) as Request;
    expect(post.headers.get("X-CSRF-Token")).toBe("token-123");
    expect(get.headers.get("X-CSRF-Token")).toBeNull();
  });

  it("convierte el formato de error de la API", () => {
    const error = toApiError(new Response(null, { status: 409 }), {
      error: { code: "last_admin", message: "Debe quedar un administrador", request_id: "r1" },
    });
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("last_admin");
    expect(error.requestId).toBe("r1");
    expect(errorMessage(error)).toBe("Debe quedar un administrador");
    expect(errorMessage(new Error("Error de red al subir una parte"))).toBe("Error de red al subir una parte");
    expect(errorMessage("x")).toBe("Error inesperado");
  });
});

describe("login", () => {
  it.each([
    [null, "/"],
    ["/configuracion?tab=trabajos", "/configuracion?tab=trabajos"],
    ["https://evil.example", "/"],
    ["//evil.example", "/"],
    ["/\\evil.example", "/"],
  ])("safeNext(%s) → %s", (input, expected) => {
    expect(safeNext(input)).toBe(expected);
  });
});

describe("CSP", () => {
  it("es estricta en producción y usa el nonce", () => {
    const csp = buildCsp("abc", false);
    expect(csp).toContain("script-src 'self' 'nonce-abc' 'strict-dynamic'");
    expect(csp).not.toContain("unsafe-eval");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("connect-src 'self'");
  });
});

describe("formato", () => {
  it("formatea valores en español", () => {
    expect(formatBytes(2_230_192)).toBe("2,1 MB");
    expect(formatBytes(null)).toBe("—");
    expect(formatDuration(3)).toBe("3,00 s");
    expect(shortId("00f50293-56c5-4082")).toBe("00f50293");
    expect(jobTypeLabel("system.render_selftest")).toBe("Autotest de render");
    expect(formatRelative(null)).toBe("nunca");
    const now = new Date("2026-10-14T12:00:00Z");
    expect(formatRelative("2026-10-14T11:58:00Z", now)).toBe("hace 2 minutos");
  });

  it("el tema rota sistema → claro → oscuro", () => {
    expect(nextThemePreference("system")).toBe("light");
    expect(nextThemePreference("light")).toBe("dark");
    expect(nextThemePreference("dark")).toBe("system");
  });
});
