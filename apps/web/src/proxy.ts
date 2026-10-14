import { NextResponse, type NextRequest } from "next/server";

/**
 * Proxy de Next.js (antes "middleware"), en el runtime de Node:
 *
 * 1. `/api/*` se reenvía a la API (DEKEN_API_INTERNAL_URL, leída en tiempo de
 *    ejecución). Así la web y la API comparten origen y las cookies son de primera parte.
 *    En producción, el proxy TLS puede enrutar `/api` directamente a la API.
 * 2. Las páginas reciben una CSP estricta con nonce por petición.
 * 3. Sin cookie de sesión, las páginas privadas redirigen a /login. La validación real
 *    de la sesión la hace siempre la API.
 */

const SESSION_COOKIE = "deken_session";
const PUBLIC_PATHS = new Set(["/login"]);

function apiBase(): string {
  return (process.env.DEKEN_API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

/** Orígenes del almacenamiento (URLs firmadas): vídeos, imágenes y subidas directas. */
function mediaOrigins(): string {
  const raw = process.env.DEKEN_MEDIA_ORIGINS ?? "http://localhost:8333";
  return raw
    .split(",")
    .map((o) => o.trim())
    .filter((o) => /^https?:\/\/[^\s;'"]+$/.test(o))
    .join(" ");
}

export function buildCsp(nonce: string, isDev: boolean): string {
  const media = mediaOrigins();
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ""}`,
    isDev ? "style-src 'self' 'unsafe-inline'" : `style-src 'self' 'nonce-${nonce}'`,
    // Atributos style (barras de progreso, anchos calculados): no ejecutan código.
    "style-src-attr 'unsafe-inline'",
    `img-src 'self' blob: data: ${media}`,
    `media-src 'self' blob: ${media}`,
    "font-src 'self'",
    // Subidas directas al almacenamiento con URLs firmadas (multiparte y marca).
    `connect-src 'self' ${media}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
}

export function proxy(request: NextRequest): NextResponse {
  const { pathname, search } = request.nextUrl;

  if (pathname.startsWith("/api/")) {
    return NextResponse.rewrite(new URL(`${pathname}${search}`, apiBase()));
  }

  const hasSession = Boolean(request.cookies.get(SESSION_COOKIE)?.value);
  if (!hasSession && !PUBLIC_PATHS.has(pathname)) {
    const login = new URL("/login", request.url);
    if (pathname !== "/") login.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(login);
  }

  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const csp = buildCsp(nonce, process.env.NODE_ENV === "development");
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "same-origin");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  return response;
}

export const config = {
  matcher: [
    "/api/:path*",
    {
      source: "/((?!_next/static|_next/image|favicon.ico|icon.svg).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
