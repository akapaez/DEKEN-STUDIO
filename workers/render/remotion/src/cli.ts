#!/usr/bin/env node
/**
 * deken-remotion-render --spec <fichero.json>
 *
 * Salida: una línea JSON por evento en stdout (`progress`, `done`, `error`).
 * Códigos de salida: 0 ok · 2 datos no válidos · 3 licencia · 130 cancelado · 1 error.
 * SIGTERM/SIGINT cancelan el render en curso.
 */
import { readFileSync } from "node:fs";

import { makeCancelSignal } from "@remotion/renderer";

import { runRender } from "./render.js";
import { RenderError, renderSpecSchema } from "./spec.js";

function emit(event: Record<string, unknown>): void {
  process.stdout.write(`${JSON.stringify(event)}\n`);
}

const EXIT: Record<string, number> = {
  invalid_spec: 2,
  invalid_timeline: 2,
  invalid_props: 2,
  unsafe_path: 2,
  remotion_license_required: 3,
};

async function main(): Promise<number> {
  const idx = process.argv.indexOf("--spec");
  const path = idx >= 0 ? process.argv[idx + 1] : undefined;
  if (!path) {
    emit({ event: "error", code: "invalid_spec", message: "Uso: deken-remotion-render --spec spec.json" });
    return 2;
  }
  const parsed = renderSpecSchema.safeParse(JSON.parse(readFileSync(path, "utf-8")));
  if (!parsed.success) {
    emit({ event: "error", code: "invalid_spec", message: "Especificación no válida", details: parsed.error.issues });
    return 2;
  }
  const { cancelSignal, cancel } = makeCancelSignal();
  let cancelled = false;
  const onSignal = () => {
    cancelled = true;
    cancel();
  };
  process.on("SIGTERM", onSignal);
  process.on("SIGINT", onSignal);
  let last = -1;
  try {
    const result = await runRender(
      parsed.data,
      (p) => {
        const pct = Math.floor(p.progress * 100);
        if (pct !== last) {
          last = pct;
          emit({ event: "progress", ...p });
        }
      },
      cancelSignal,
    );
    emit({ event: "done", ...result });
    return 0;
  } catch (err) {
    if (cancelled) {
      emit({ event: "error", code: "cancelled", message: "Render cancelado" });
      return 130;
    }
    if (err instanceof RenderError) {
      emit({ event: "error", code: err.code, message: err.message, details: err.details ?? null });
      return EXIT[err.code] ?? 1;
    }
    emit({ event: "error", code: "render_failed", message: err instanceof Error ? err.message : String(err) });
    return 1;
  }
}

main().then(
  (code) => process.exit(code),
  (err: unknown) => {
    emit({ event: "error", code: "render_failed", message: String(err) });
    process.exit(1);
  },
);
