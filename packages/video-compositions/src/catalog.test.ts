import { describe, expect, it } from "vitest";

import { FORMATS } from "./formats";
import { arriveFrames, cameraPush, MAX_CAMERA_PUSH } from "./motion";
import { evaluationDefaults, evaluationPropsSchema } from "./schema/evaluation";
import { MIN_TEXT_PX } from "./schema/timeline";
import { TEMPLATES, templateById } from "./templates/catalog";

describe("catálogo de plantillas", () => {
  it("contiene los 10 tipos de pieza del brief", () => {
    expect(TEMPLATES.map((t) => t.id)).toEqual([
      "reel_vertical",
      "horizontal_16_9",
      "square_post",
      "educational",
      "industrial_process",
      "product_showcase",
      "b2b_commercial",
      "technical_comparison",
      "brand_animation",
      "corporate_intro_outro",
    ]);
    expect(templateById("industrial_process")?.formats.length).toBeGreaterThan(0);
  });

  it.each(TEMPLATES.map((t) => [t.id, t] as const))("%s es coherente", (_id, t) => {
    expect(t.id).toMatch(/^[a-z0-9_]{1,64}$/); // válido como `template` de la línea de tiempo
    expect(t.formats.length).toBeGreaterThan(0);
    for (const f of t.formats) expect(FORMATS[f]).toBeDefined();
    expect(t.duration_seconds.min).toBeLessThanOrEqual(t.duration_seconds.max);
    expect(new Set(t.slots.map((s) => s.id)).size).toBe(t.slots.length);
    for (const slot of t.slots) {
      expect(slot.min_seconds).toBeLessThanOrEqual(slot.max_seconds);
      if (slot.kind === "text") expect(slot.min_seconds).toBeGreaterThanOrEqual(2.5);
    }
    // Toda pieza termina con la marca.
    expect(t.slots.at(-1)?.kind).toBe("brand_outro");
  });
});

describe("formatos y zonas seguras", () => {
  it.each(Object.values(FORMATS).map((f) => [f.id, f] as const))("%s deja un área útil amplia", (_id, f) => {
    const usableW = f.width - f.safe.left - f.safe.right;
    const usableH = f.height - f.safe.top - f.safe.bottom;
    expect(usableW / f.width).toBeGreaterThan(0.7);
    expect(usableH / f.height).toBeGreaterThan(0.6);
    expect(Object.values(f.safe).every((v) => v > 0)).toBe(true);
    // El texto mínimo cabe holgadamente en el área segura.
    expect(usableW).toBeGreaterThan(MIN_TEXT_PX * 10);
  });
});

describe("movimiento de marca", () => {
  it("las llegadas duran entre 0,5 y 0,8 s", () => {
    for (const fps of [24, 25, 30, 60]) {
      const seconds = arriveFrames(fps) / fps;
      expect(seconds).toBeGreaterThanOrEqual(0.5);
      expect(seconds).toBeLessThanOrEqual(0.8);
    }
  });

  it("el empuje de cámara nunca supera el 6 %", () => {
    expect(cameraPush(100, 100, 0.5)).toBeCloseTo(1 + MAX_CAMERA_PUSH);
    expect(cameraPush(0, 100)).toBe(1);
    expect(cameraPush(500, 100, 0.04)).toBeCloseTo(1.04);
  });
});

describe("composición de evaluación", () => {
  it("tiene propiedades editables y acotadas", () => {
    expect(evaluationDefaults.title).toBe("DEKEN STUDIO AI");
    expect(evaluationPropsSchema.safeParse({ title: "x".repeat(41) }).success).toBe(false);
    expect(evaluationPropsSchema.safeParse({ token: "secreto" }).success).toBe(false);
  });
});
