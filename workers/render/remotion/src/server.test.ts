import { mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { confined, type InputServer, startInputServer } from "./server";

let root: string;
let outside: string;
let server: InputServer;

beforeAll(async () => {
  root = mkdtempSync(join(tmpdir(), "deken-inputs-"));
  outside = mkdtempSync(join(tmpdir(), "deken-outside-"));
  writeFileSync(join(root, "clip.mp4"), Buffer.from("0123456789"));
  writeFileSync(join(outside, "secreto.txt"), "no");
  mkdirSync(join(root, "sub"));
  symlinkSync(join(outside, "secreto.txt"), join(root, "sub", "enlace.txt"));
  server = await startInputServer(root);
});

afterAll(async () => {
  await server.close();
});

describe("confined", () => {
  it("permite ficheros del directorio del trabajo", () => {
    expect(confined(root, "clip.mp4")).toMatch(/clip\.mp4$/);
  });

  it("rechaza salir del directorio (.. y enlaces simbólicos)", () => {
    expect(() => confined(root, "../" + outside.split("/").pop() + "/secreto.txt")).toThrow();
    expect(() => confined(root, "/etc/hostname")).toThrow();
    expect(() => confined(root, "sub/enlace.txt")).toThrow();
  });
});

describe("servidor de entradas", () => {
  it("sirve el fichero completo con su tipo", async () => {
    const res = await fetch(server.urlFor("clip.mp4"));
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toBe("video/mp4");
    expect(await res.text()).toBe("0123456789");
  });

  it("admite peticiones Range, incluidas las de sufijo", async () => {
    const part = await fetch(server.urlFor("clip.mp4"), { headers: { Range: "bytes=2-4" } });
    expect(part.status).toBe(206);
    expect(part.headers.get("content-range")).toBe("bytes 2-4/10");
    expect(await part.text()).toBe("234");
    const open = await fetch(server.urlFor("clip.mp4"), { headers: { Range: "bytes=7-" } });
    expect(await open.text()).toBe("789");
    const suffix = await fetch(server.urlFor("clip.mp4"), { headers: { Range: "bytes=-3" } });
    expect(suffix.status).toBe(206);
    expect(await suffix.text()).toBe("789");
    const beyond = await fetch(server.urlFor("clip.mp4"), { headers: { Range: "bytes=50-" } });
    expect(beyond.status).toBe(416);
    expect(beyond.headers.get("content-range")).toBe("bytes */10");
  });

  it("exige el token aleatorio de la ruta y no sale del directorio", async () => {
    const url = new URL(server.urlFor("clip.mp4"));
    const noToken = await fetch(`${url.origin}/f/otro/clip.mp4`);
    expect(noToken.status).toBe(404);
    const escape = await fetch(server.urlFor("sub/enlace.txt"));
    expect(escape.status).toBe(404);
    expect(url.hostname).toBe("127.0.0.1");
  });

  it("solo admite GET y HEAD", async () => {
    const res = await fetch(server.urlFor("clip.mp4"), { method: "POST" });
    expect(res.status).toBe(405);
  });
});
