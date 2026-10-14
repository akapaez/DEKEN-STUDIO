import { describe, expect, it, vi } from "vitest";

import { NAV_ITEMS, isActive } from "./nav";
import {
  PART_ATTEMPTS,
  PartUploadError,
  isAbort,
  planParts,
  uploadMediaFile,
  type PartTransport,
  type UploadApi,
  type UploadState,
} from "./upload";

const MB = 1024 * 1024;

function fakeApi(partSize: number, size: number, maxPerRequest = 2) {
  const calls = { partUrls: [] as number[][], aborted: 0, completed: 0 };
  const client: UploadApi = {
    start: vi.fn(async () => ({
      asset_id: "a1",
      part_size_bytes: partSize,
      part_count: Math.ceil(size / partSize),
      max_parts_per_request: maxPerRequest,
    })),
    partUrls: vi.fn(async (_id: string, numbers: number[]) => {
      calls.partUrls.push(numbers);
      return numbers.map((n) => ({ part_number: n, url: `https://s3.test/part/${n}?v=${calls.partUrls.length}` }));
    }),
    complete: vi.fn(async () => {
      calls.completed += 1;
      return { id: "a1", status: "processing" } as never;
    }),
    abort: vi.fn(async () => {
      calls.aborted += 1;
    }),
  };
  return { client, calls };
}

const file = (size: number) => new File([new Uint8Array(size)], "corte.mp4", { type: "video/mp4" });

describe("planParts", () => {
  it("divide el fichero en partes contiguas sin solapes", () => {
    const parts = planParts(10 * MB + 1, 5 * MB);
    expect(parts.map((p) => p.number)).toEqual([1, 2, 3]);
    expect(parts[2]).toEqual({ number: 3, start: 10 * MB, end: 10 * MB + 1 });
    expect(parts.reduce((n, p) => n + (p.end - p.start), 0)).toBe(10 * MB + 1);
    expect(planParts(0, 5 * MB)).toEqual([]);
  });
});

describe("uploadMediaFile", () => {
  it("sube todas las partes con URLs por lotes y cierra la subida", async () => {
    const size = 5 * 1024;
    const { client, calls } = fakeApi(1024, size);
    const sent = new Map<number, number>();
    const transport: PartTransport = async (url, body, onProgress) => {
      const n = Number(/part\/(\d+)/.exec(url)?.[1]);
      sent.set(n, body.size);
      onProgress(body.size);
    };
    const states: UploadState[] = [];
    const asset = await uploadMediaFile(file(size), {
      signal: new AbortController().signal,
      onState: (s) => states.push(s),
      client,
      transport,
      concurrency: 2,
    });
    expect(asset.id).toBe("a1");
    expect([...sent.keys()].sort()).toEqual([1, 2, 3, 4, 5]);
    expect([...sent.values()].reduce((a, b) => a + b, 0)).toBe(size);
    // Lotes de 2 URLs como máximo, sin pedir dos veces el mismo lote.
    expect(calls.partUrls).toEqual([[1, 2], [3, 4], [5]]);
    expect(calls.completed).toBe(1);
    expect(states.at(-1)).toMatchObject({ phase: "done", loaded: size, total: size });
    expect(states.some((s) => s.phase === "verifying")).toBe(true);
  });

  it("reintenta una parte con una URL nueva", async () => {
    const { client, calls } = fakeApi(1024, 2048);
    let failures = 1;
    const transport: PartTransport = async (url) => {
      if (url.includes("part/2") && failures > 0) {
        failures -= 1;
        throw new PartUploadError(403);
      }
    };
    await uploadMediaFile(file(2048), {
      signal: new AbortController().signal,
      onState: () => undefined,
      client,
      transport,
      retryDelayMs: 1,
    });
    expect(calls.partUrls).toContainEqual([2]); // URL renovada para el reintento
    expect(calls.completed).toBe(1);
  });

  it("tras agotar los reintentos aborta la subida en el almacenamiento", async () => {
    const { client, calls } = fakeApi(1024, 1024);
    const transport = vi.fn<PartTransport>(async () => {
      throw new PartUploadError(0);
    });
    const states: UploadState[] = [];
    await expect(
      uploadMediaFile(file(1024), {
        signal: new AbortController().signal,
        onState: (s) => states.push(s),
        client,
        transport,
        retryDelayMs: 1,
      }),
    ).rejects.toBeInstanceOf(PartUploadError);
    expect(transport).toHaveBeenCalledTimes(PART_ATTEMPTS);
    expect(calls.aborted).toBe(1);
    expect(calls.completed).toBe(0);
    expect(states.at(-1)?.phase).toBe("failed");
  });

  it("cancelar detiene la subida y la aborta", async () => {
    const { client, calls } = fakeApi(1024, 4096);
    const controller = new AbortController();
    const transport: PartTransport = (_url, _body, _progress, signal) =>
      new Promise((_resolve, reject) => {
        signal.addEventListener("abort", () => reject(new DOMException("x", "AbortError")));
        setTimeout(() => controller.abort(), 5);
      });
    const states: UploadState[] = [];
    const error = await uploadMediaFile(file(4096), {
      signal: controller.signal,
      onState: (s) => states.push(s),
      client,
      transport,
    }).catch((e: unknown) => e);
    expect(isAbort(error)).toBe(true);
    expect(calls.aborted).toBe(1);
    expect(calls.completed).toBe(0);
    expect(states.at(-1)?.phase).toBe("cancelled");
  });
});

describe("navegación de Sprint 1", () => {
  it("Biblioteca y Marca están disponibles; las fichas activan la Biblioteca", () => {
    const library = NAV_ITEMS.find((i) => i.id === "library")!;
    const brand = NAV_ITEMS.find((i) => i.id === "brand")!;
    expect(library.href).toBe("/biblioteca");
    expect(brand.href).toBe("/marca");
    expect(isActive(library, "/biblioteca/123")).toBe(true);
    expect(NAV_ITEMS.filter((i) => i.href === null).map((i) => i.availability)).not.toContain("Sprint 1");
  });
});
