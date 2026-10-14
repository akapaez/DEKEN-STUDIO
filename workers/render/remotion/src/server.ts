/**
 * Servidor HTTP mínimo, solo en 127.0.0.1, que expone a Remotion los ficheros de
 * entrada del trabajo. Rutas con un token aleatorio y confinadas al directorio del
 * trabajo; admite peticiones Range (búsqueda en vídeo).
 */
import { randomBytes } from "node:crypto";
import { createReadStream, realpathSync, statSync } from "node:fs";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { extname, resolve, sep } from "node:path";

const TYPES: Record<string, string> = {
  ".mp4": "video/mp4",
  ".mov": "video/quicktime",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".m4a": "audio/mp4",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
};

export interface InputServer {
  urlFor(file: string): string;
  close(): Promise<void>;
}

export function confined(root: string, file: string): string {
  const base = realpathSync(root);
  const target = realpathSync(resolve(base, file));
  if (target !== base && !target.startsWith(base + sep)) {
    throw new Error(`Ruta fuera del directorio del trabajo: ${file}`);
  }
  return target;
}

export async function startInputServer(root: string): Promise<InputServer> {
  const token = randomBytes(16).toString("hex");
  const prefix = `/f/${token}/`;
  const server: Server = createServer((req, res) => {
    try {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      if (req.method !== "GET" && req.method !== "HEAD") {
        res.writeHead(405).end();
        return;
      }
      if (!url.pathname.startsWith(prefix)) {
        res.writeHead(404).end();
        return;
      }
      const file = confined(root, decodeURIComponent(url.pathname.slice(prefix.length)));
      const size = statSync(file).size;
      const type = TYPES[extname(file).toLowerCase()] ?? "application/octet-stream";
      const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range ?? "");
      const headers = { "Content-Type": type, "Accept-Ranges": "bytes", "Access-Control-Allow-Origin": "*" };
      if (range && (range[1] || range[2])) {
        // "bytes=-N" son los N últimos bytes (RFC 9110).
        const suffix = !range[1];
        const start = suffix ? Math.max(0, size - Number(range[2])) : Number(range[1]);
        const end = suffix || !range[2] ? size - 1 : Math.min(Number(range[2]), size - 1);
        if (start > end || start >= size) {
          res.writeHead(416, { "Content-Range": `bytes */${size}` }).end();
          return;
        }
        res.writeHead(206, { ...headers, "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": end - start + 1 });
        if (req.method === "HEAD") return void res.end();
        createReadStream(file, { start, end }).pipe(res);
        return;
      }
      res.writeHead(200, { ...headers, "Content-Length": size });
      if (req.method === "HEAD") return void res.end();
      createReadStream(file).pipe(res);
    } catch {
      res.writeHead(404).end();
    }
  });
  await new Promise<void>((ok) => server.listen(0, "127.0.0.1", ok));
  const port = (server.address() as AddressInfo).port;
  return {
    urlFor: (file: string) => `http://127.0.0.1:${port}${prefix}${encodeURIComponent(file)}`,
    close: () => new Promise<void>((ok) => server.close(() => ok())),
  };
}
