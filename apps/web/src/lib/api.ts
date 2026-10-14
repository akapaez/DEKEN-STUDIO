/**
 * Cliente tipado de la API v1 (tipos generados desde OpenAPI en @deken/shared).
 *
 * - Mismo origen: la cookie de sesión viaja sola (HttpOnly); el navegador nunca ve
 *   credenciales de proveedores.
 * - Peticiones no seguras: añade la cabecera CSRF leída de la cookie `deken_csrf`.
 */
import type { paths } from "@deken/shared";
import createClient, { type Middleware } from "openapi-fetch";

export const CSRF_COOKIE = "deken_csrf";
export const CSRF_HEADER = "X-CSRF-Token";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  readonly requestId: string | null;

  constructor(status: number, code: string, message: string, details?: unknown, requestId?: string | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId ?? null;
  }
}

export function readCookie(name: string, cookieString?: string): string | null {
  const source = cookieString ?? (typeof document === "undefined" ? "" : document.cookie);
  for (const part of source.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

export const csrfMiddleware: Middleware = {
  onRequest({ request }) {
    if (!SAFE_METHODS.has(request.method.toUpperCase())) {
      const token = readCookie(CSRF_COOKIE);
      if (token) request.headers.set(CSRF_HEADER, token);
    }
    return request;
  },
};

export function toApiError(response: Response, error: unknown): ApiError {
  const body = (error ?? {}) as { error?: { code?: string; message?: string; details?: unknown; request_id?: string } };
  const info = body.error ?? {};
  return new ApiError(
    response.status,
    info.code ?? "http_error",
    info.message ?? `Error ${response.status}`,
    info.details,
    info.request_id ?? response.headers.get("x-request-id"),
  );
}

export const api = createClient<paths>({
  baseUrl: typeof window === "undefined" ? "http://localhost" : window.location.origin,
  credentials: "same-origin",
});
api.use(csrfMiddleware);

interface FetchResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/** Devuelve los datos o lanza ApiError con el formato de error uniforme de la API. */
export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw new ApiError(0, "network_error", "No se puede conectar con la API. Revisa tu conexión.");
  }
  const { data, error, response } = result;
  if (!response.ok || error !== undefined) throw toApiError(response, error);
  return data as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "validation_error" && Array.isArray(error.details)) {
      const first = error.details[0] as { msg?: string; loc?: unknown[] } | undefined;
      if (first?.msg) return `Datos no válidos: ${first.msg}`;
    }
    return error.message;
  }
  if (error instanceof Error && error.message) return error.message;
  return "Error inesperado";
}
