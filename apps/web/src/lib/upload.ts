/**
 * Subida multiparte de vídeos MP4/MOV directa al almacenamiento.
 *
 * 1. La API crea la subida y fija el tamaño de parte (POST /media/uploads).
 * 2. El navegador pide URLs firmadas por lotes y sube cada parte con PUT (varias a la vez,
 *    con reintentos). Las credenciales del almacenamiento nunca llegan al navegador.
 * 3. La API cierra la subida: comprueba las partes en el servidor, valida el fichero con
 *    ffprobe y encola la ingesta. El original queda inmutable.
 * Cancelar aborta la subida en el almacenamiento (no quedan partes huérfanas).
 */
import type { Schemas } from "@deken/shared";

import { api, unwrap } from "./api";

type MediaAssetDetail = Schemas["MediaAssetDetailOut"];

export interface UploadPlan {
  asset_id: string;
  part_size_bytes: number;
  part_count: number;
  max_parts_per_request: number;
}

export interface UploadApi {
  start(body: { filename: string; size_bytes: number; content_type: string; title?: string | null }): Promise<UploadPlan>;
  partUrls(assetId: string, partNumbers: number[]): Promise<Array<{ part_number: number; url: string }>>;
  complete(assetId: string): Promise<MediaAssetDetail>;
  abort(assetId: string): Promise<void>;
}

/** Sube un trozo a una URL firmada; informa de los bytes enviados. */
export type PartTransport = (
  url: string,
  body: Blob,
  onProgress: (loaded: number) => void,
  signal: AbortSignal,
) => Promise<void>;

export type UploadPhase = "starting" | "uploading" | "verifying" | "done" | "failed" | "cancelled";

export interface UploadState {
  phase: UploadPhase;
  loaded: number;
  total: number;
  assetId?: string;
}

export interface PartRange {
  number: number;
  start: number;
  end: number;
}

export class PartUploadError extends Error {
  constructor(readonly status: number) {
    super(status ? `El almacenamiento respondió ${status}` : "Error de red al subir una parte");
    this.name = "PartUploadError";
  }
}

export const PART_ATTEMPTS = 4;
export const UPLOAD_CONCURRENCY = 3;

export function planParts(size: number, partSize: number): PartRange[] {
  if (size <= 0 || partSize <= 0) return [];
  const parts: PartRange[] = [];
  for (let start = 0, n = 1; start < size; start += partSize, n += 1) {
    parts.push({ number: n, start, end: Math.min(size, start + partSize) });
  }
  return parts;
}

const abortError = () => new DOMException("Subida cancelada", "AbortError");

export const isAbort = (err: unknown) => err instanceof DOMException && err.name === "AbortError";

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(abortError());
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(abortError());
      },
      { once: true },
    );
  });
}

export const apiUploadClient: UploadApi = {
  start: (body) => unwrap(api.POST("/api/v1/media/uploads", { body })),
  partUrls: (assetId, partNumbers) =>
    unwrap(
      api.POST("/api/v1/media/uploads/{asset_id}/parts", {
        params: { path: { asset_id: assetId } },
        body: { part_numbers: partNumbers },
      }),
    ),
  complete: (assetId) =>
    unwrap(api.POST("/api/v1/media/uploads/{asset_id}/complete", { params: { path: { asset_id: assetId } } })),
  abort: async (assetId) => {
    await unwrap(api.POST("/api/v1/media/uploads/{asset_id}/abort", { params: { path: { asset_id: assetId } } }));
  },
};

export const xhrTransport: PartTransport = (url, body, onProgress, signal) =>
  new Promise((resolve, reject) => {
    if (signal.aborted) return reject(abortError());
    const xhr = new XMLHttpRequest();
    const onAbort = () => xhr.abort();
    xhr.open("PUT", url);
    xhr.upload.onprogress = (event) => onProgress(event.loaded);
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new PartUploadError(xhr.status)));
    xhr.onerror = () => reject(new PartUploadError(0));
    xhr.onabort = () => reject(abortError());
    xhr.onloadend = () => signal.removeEventListener("abort", onAbort);
    signal.addEventListener("abort", onAbort, { once: true });
    xhr.send(body);
  });

export interface UploadOptions {
  title?: string | null;
  signal: AbortSignal;
  onState: (state: UploadState) => void;
  concurrency?: number;
  client?: UploadApi;
  transport?: PartTransport;
  retryDelayMs?: number;
}

export async function uploadMediaFile(file: File, options: UploadOptions): Promise<MediaAssetDetail> {
  const { signal, onState } = options;
  const client = options.client ?? apiUploadClient;
  const transport = options.transport ?? xhrTransport;
  const retryDelay = options.retryDelayMs ?? 1000;
  const total = file.size;
  onState({ phase: "starting", loaded: 0, total });

  const plan = await client.start({
    filename: file.name,
    size_bytes: file.size,
    content_type: file.type,
    title: options.title ?? null,
  });
  const assetId = plan.asset_id;
  const parts = planParts(file.size, plan.part_size_bytes);

  const cancel = async (): Promise<never> => {
    await client.abort(assetId).catch(() => undefined);
    onState({ phase: "cancelled", loaded: 0, total, assetId });
    throw abortError();
  };

  try {
    if (parts.length !== plan.part_count) throw new Error("El plan de subida no coincide con el fichero");
    const progress = new Map<number, number>();
    const report = () => {
      let loaded = 0;
      for (const v of progress.values()) loaded += v;
      onState({ phase: "uploading", loaded, total, assetId });
    };
    report();

    // URLs firmadas por lotes, pedidas justo antes de usarlas (caducan).
    const urls = new Map<number, string>();
    const batches = new Map<number, Promise<void>>();
    const batchSize = Math.max(1, plan.max_parts_per_request);
    const urlFor = async (n: number, fresh = false): Promise<string> => {
      if (fresh) {
        urls.delete(n);
        const [one] = await client.partUrls(assetId, [n]);
        if (!one) throw new Error(`Sin URL para la parte ${n}`);
        urls.set(n, one.url);
      }
      const cached = urls.get(n);
      if (cached) return cached;
      const batch = Math.floor((n - 1) / batchSize);
      let pending = batches.get(batch);
      if (!pending) {
        const numbers = parts.slice(batch * batchSize, (batch + 1) * batchSize).map((p) => p.number);
        pending = client.partUrls(assetId, numbers).then((list) => {
          for (const item of list) urls.set(item.part_number, item.url);
        });
        batches.set(batch, pending);
      }
      await pending;
      const url = urls.get(n);
      if (!url) throw new Error(`Sin URL para la parte ${n}`);
      return url;
    };

    const uploadPart = async (part: PartRange) => {
      const body = file.slice(part.start, part.end);
      for (let attempt = 1; ; attempt += 1) {
        if (signal.aborted) throw abortError();
        try {
          const url = await urlFor(part.number, attempt > 1);
          await transport(
            url,
            body,
            (loaded) => {
              progress.set(part.number, loaded);
              report();
            },
            signal,
          );
          progress.set(part.number, part.end - part.start);
          report();
          return;
        } catch (err) {
          if (isAbort(err) || signal.aborted) throw abortError();
          progress.set(part.number, 0);
          if (attempt >= PART_ATTEMPTS) throw err;
          await sleep(retryDelay * 2 ** (attempt - 1), signal);
        }
      }
    };

    const queue = [...parts];
    const workers = Array.from({ length: Math.min(options.concurrency ?? UPLOAD_CONCURRENCY, parts.length) }, async () => {
      for (let part = queue.shift(); part; part = queue.shift()) await uploadPart(part);
    });
    await Promise.all(workers);
    if (signal.aborted) throw abortError();

    onState({ phase: "verifying", loaded: total, total, assetId });
    const asset = await client.complete(assetId);
    onState({ phase: "done", loaded: total, total, assetId });
    return asset;
  } catch (err) {
    if (isAbort(err) || signal.aborted) return cancel();
    // Fallo definitivo: se aborta en el almacenamiento para no dejar partes huérfanas.
    await client.abort(assetId).catch(() => undefined);
    onState({ phase: "failed", loaded: 0, total, assetId });
    throw err;
  }
}

/** Sube un recurso de marca (logo, tipografía o imagen): PUT firmado + análisis en la API. */
export async function uploadBrandFile(
  file: File,
  body: { kind: "logo" | "font" | "image"; name: string; license_ref?: string | null },
): Promise<Schemas["BrandAssetOut"]> {
  const plan = await unwrap(
    api.POST("/api/v1/brand/uploads", {
      body: { ...body, filename: file.name, size_bytes: file.size },
    }),
  );
  let put: Response;
  try {
    put = await fetch(plan.upload_url, { method: "PUT", body: file, headers: plan.headers });
  } catch {
    throw new PartUploadError(0);
  }
  if (!put.ok) throw new PartUploadError(put.status);
  return unwrap(api.POST("/api/v1/brand/uploads/{asset_id}/complete", { params: { path: { asset_id: plan.asset_id } } }));
}
