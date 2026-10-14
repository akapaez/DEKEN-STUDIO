/**
 * Especificación de un render que el worker (Python) entrega al motor Remotion.
 * Solo contiene rutas locales del directorio aislado del trabajo: ni claves de
 * almacenamiento ni URLs firmadas llegan a la composición.
 */
import { z } from "zod";

export const LICENSE_MODES = ["evaluation", "company"] as const;

export const renderInputSchema = z
  .object({
    key: z.string().regex(/^(asset|brand):[0-9a-f-]{36}$/),
    file: z.string().min(1),
    kind: z.enum(["video", "image", "audio"]),
    width: z.number().int().positive().optional(),
    height: z.number().int().positive().optional(),
    duration_s: z.number().positive().optional(),
    has_audio: z.boolean().optional(),
  })
  .strict();

export const renderSpecSchema = z
  .object({
    composition: z.enum(["DekenEvaluation", "DekenTimeline"]),
    props: z.record(z.string(), z.unknown()),
    purpose: z.enum(["evaluation", "production"]),
    output_path: z.string().min(1),
    work_dir: z.string().min(1),
    inputs: z.array(renderInputSchema).max(500).default([]),
    license: z.object({ mode: z.enum(LICENSE_MODES), key: z.string().optional() }).strict(),
    bundle_dir: z.string().min(1),
    browser_executable: z.string().optional(),
    concurrency: z.number().int().min(1).max(16).optional(),
    timeout_ms: z.number().int().min(10_000).max(3_600_000).default(120_000),
  })
  .strict();

export type RenderSpec = z.infer<typeof renderSpecSchema>;
export type RenderInput = z.infer<typeof renderInputSchema>;

export class RenderError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly details?: unknown,
  ) {
    super(message);
    this.name = "RenderError";
  }
}

/**
 * Puerta de licencia: sin licencia de empresa verificada solo se permiten renders de
 * evaluación (que además llevan marca de agua). Ver ADR 0005.
 */
export function licenseFor(spec: Pick<RenderSpec, "license" | "purpose">): {
  licenseKey: string;
  isProduction: boolean;
} {
  if (spec.purpose === "production") {
    if (spec.license.mode !== "company" || !spec.license.key) {
      throw new RenderError(
        "remotion_license_required",
        "Los renders de producción con Remotion requieren la licencia de empresa verificada",
      );
    }
    return { licenseKey: spec.license.key, isProduction: true };
  }
  if (spec.license.mode === "company" && spec.license.key) {
    return { licenseKey: spec.license.key, isProduction: false };
  }
  return { licenseKey: "free-license", isProduction: false };
}
