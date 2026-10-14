import { describe, expect, it } from "vitest";

import { licenseFor, RenderError, renderSpecSchema } from "./spec";

const base = {
  composition: "DekenTimeline",
  props: {},
  purpose: "evaluation",
  output_path: "/w/render.mp4",
  work_dir: "/w",
  license: { mode: "evaluation" },
  bundle_dir: "/b",
} as const;

describe("puerta de licencia (ADR 0005)", () => {
  it("evaluación sin licencia de empresa: licencia gratuita y no producción", () => {
    expect(licenseFor({ purpose: "evaluation", license: { mode: "evaluation" } })).toEqual({
      licenseKey: "free-license",
      isProduction: false,
    });
  });

  it("producción exige modo empresa y clave", () => {
    for (const license of [{ mode: "evaluation" as const }, { mode: "company" as const }]) {
      expect(() => licenseFor({ purpose: "production", license })).toThrowError(RenderError);
    }
    try {
      licenseFor({ purpose: "production", license: { mode: "evaluation", key: "k" } });
    } catch (error) {
      expect((error as RenderError).code).toBe("remotion_license_required");
    }
    expect(licenseFor({ purpose: "production", license: { mode: "company", key: "k" } })).toEqual({
      licenseKey: "k",
      isProduction: true,
    });
  });

  it("con licencia de empresa, la evaluación usa la clave pero no cuenta como producción", () => {
    expect(licenseFor({ purpose: "evaluation", license: { mode: "company", key: "k" } })).toEqual({
      licenseKey: "k",
      isProduction: false,
    });
  });
});

describe("especificación de render", () => {
  it("acepta la especificación mínima y aplica valores por defecto", () => {
    const spec = renderSpecSchema.parse(base);
    expect(spec.inputs).toEqual([]);
    expect(spec.timeout_ms).toBe(120_000);
  });

  it("rechaza campos desconocidos (p. ej. credenciales de almacenamiento)", () => {
    expect(renderSpecSchema.safeParse({ ...base, s3_secret_key: "x" }).success).toBe(false);
    expect(
      renderSpecSchema.safeParse({
        ...base,
        inputs: [{ key: "asset:00000000-0000-0000-0000-000000000000", file: "a.mp4", kind: "video", url: "https://x" }],
      }).success,
    ).toBe(false);
  });

  it("solo admite claves de medios asset:/brand: con UUID", () => {
    const input = { file: "a.mp4", kind: "video" };
    expect(renderSpecSchema.safeParse({ ...base, inputs: [{ ...input, key: "s3://bucket/a" }] }).success).toBe(false);
    expect(
      renderSpecSchema.safeParse({ ...base, inputs: [{ ...input, key: "brand:6f9619ff-8b86-d011-b42d-00cf4fc964ff" }] })
        .success,
    ).toBe(true);
  });

  it("solo renderiza composiciones registradas", () => {
    expect(renderSpecSchema.safeParse({ ...base, composition: "Otra" }).success).toBe(false);
  });
});
