import { describe, expect, it } from "vitest";

import { FORMATS, type FormatId } from "../formats";
import { centeredCoverReframe, placeContain, placeReframe, reframeMatchesOutput } from "./geometry";
import { emptyTimeline, timelineSchema, type TimelineInput } from "./timeline";
import { parseTimeline, semanticIssues } from "./validate";

const ASSET = "3b241101-e2bb-4255-8caf-4136c566a962";
const LOGO = "0f8fad5b-d9cb-469f-a165-70867728950e";

function vertical(tracks: TimelineInput["tracks"], seconds = 10): TimelineInput {
  return { ...emptyTimeline("vertical_9_16", seconds), tracks };
}

const messages = (input: TimelineInput) => {
  const result = parseTimeline(input);
  return result.ok ? [] : result.issues.map((i) => i.message);
};

describe("esquema deken.timeline/1", () => {
  it("acepta un documento mínimo y rellena los valores por defecto", () => {
    const result = parseTimeline(
      vertical([{ id: "t", kind: "text", clips: [{ id: "a", text: "Hola", at_frame: 0, duration_frames: 90 }] }]),
    );
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    const track = result.timeline.tracks[0]!;
    expect(track.kind === "text" && track.clips[0]).toMatchObject({ size_px: 96, weight: 900, box: true });
  });

  it("el formato fija el tamaño exacto de la salida", () => {
    const wrong = { ...emptyTimeline("vertical_9_16", 5), output: { ...emptyTimeline("vertical_9_16", 5).output, width: 1920 } };
    expect(timelineSchema.safeParse(wrong).success).toBe(false);
    for (const id of Object.keys(FORMATS) as FormatId[]) {
      expect(timelineSchema.safeParse(emptyTimeline(id, 5)).success).toBe(true);
    }
  });

  it("limita la duración a 10 minutos según la cadencia", () => {
    const long = emptyTimeline("square_1_1", 1);
    long.output.duration_frames = 30 * 600 + 1;
    expect(timelineSchema.safeParse(long).success).toBe(false);
    long.output.duration_frames = 30 * 600;
    expect(timelineSchema.safeParse(long).success).toBe(true);
  });

  it("rechaza propiedades desconocidas (no se cuelan URLs ni claves)", () => {
    const withUrl = vertical([
      { id: "v", kind: "video", clips: [{ id: "c", asset_id: ASSET, source_in_s: 0, source_out_s: 2, at_frame: 0, url: "https://x" } as never] },
    ]);
    expect(timelineSchema.safeParse(withUrl).success).toBe(false);
  });

  it("rechaza reencuadres fuera de la imagen y textos por debajo de 30 px", () => {
    expect(
      messages(
        vertical([
          {
            id: "v",
            kind: "video",
            clips: [{ id: "c", asset_id: ASSET, source_in_s: 0, source_out_s: 2, at_frame: 0, reframe: { x: 0.8, y: 0, w: 0.4, h: 1 } }],
          },
        ]),
      ),
    ).toContain("el reencuadre se sale de la imagen");
    expect(
      parseTimeline(vertical([{ id: "t", kind: "text", clips: [{ id: "a", text: "x", at_frame: 0, duration_frames: 90, size_px: 20 }] }])).ok,
    ).toBe(false);
  });
});

describe("reglas semánticas", () => {
  it("texto visible al menos 2,5 s y dentro de la duración", () => {
    const issues = messages(
      vertical([
        {
          id: "t",
          kind: "text",
          clips: [
            { id: "a", text: "Corto", at_frame: 0, duration_frames: 30 },
            { id: "b", text: "Tarde", at_frame: 280, duration_frames: 90 },
          ],
        },
      ]),
    );
    expect(issues).toContain("un texto debe verse al menos 2,5 s");
    expect(issues).toContain("el clip termina después del final");
  });

  it("el logo nunca aparece en los 3 primeros segundos", () => {
    const early = vertical([{ id: "m", kind: "brand", clips: [{ id: "l", brand_asset_id: LOGO, at_frame: 60, duration_frames: 60 }] }]);
    expect(messages(early)).toContain("el logo no puede aparecer en los 3 primeros segundos");
    const late = vertical([{ id: "m", kind: "brand", clips: [{ id: "l", brand_asset_id: LOGO, at_frame: 90, duration_frames: 60 }] }]);
    expect(messages(late)).toEqual([]);
  });

  it("detecta solapes de vídeo salvo durante la transición de entrada", () => {
    const clip = (id: string, at: number, transition = 0) => ({
      id,
      asset_id: ASSET,
      source_in_s: 0,
      source_out_s: 2,
      at_frame: at,
      transition_in: { type: transition ? ("fade" as const) : ("cut" as const), frames: transition },
    });
    expect(messages(vertical([{ id: "v", kind: "video", clips: [clip("a", 0), clip("b", 50)] }]))).toContain(
      "clips de vídeo solapados",
    );
    expect(messages(vertical([{ id: "v", kind: "video", clips: [clip("a", 0), clip("b", 50, 10)] }]))).toEqual([]);
  });

  it("la música necesita referencia de licencia", () => {
    const music = (license_ref?: string) =>
      vertical([
        { id: "m", kind: "audio", role: "music", clips: [{ id: "s", asset_id: ASSET, at_frame: 0, duration_frames: 90, ...(license_ref ? { license_ref } : {}) }] },
      ]);
    expect(messages(music())).toContain("la música necesita referencia de licencia");
    expect(messages(music("LIC-2026-001"))).toEqual([]);
  });

  it("con medios resueltos: autorizados, duración real y reencuadre sin deformar", () => {
    const parsed = timelineSchema.parse(
      vertical([
        {
          id: "v",
          kind: "video",
          clips: [{ id: "c", asset_id: ASSET, source_in_s: 0, source_out_s: 8, at_frame: 0, reframe: { x: 0, y: 0, w: 1, h: 1 } }],
        },
      ]),
    );
    expect(semanticIssues(parsed, {}).map((i) => i.message)).toContain("medio no resuelto o no autorizado");
    const issues = semanticIssues(parsed, {
      [`asset:${ASSET}`]: { src: "a.mp4", kind: "video", width: 1920, height: 1080, duration_s: 6 },
    }).map((i) => i.message);
    expect(issues).toContain("source_out_s supera la duración del original");
    expect(issues).toContain("el reencuadre deformaría la imagen");
  });
});

describe("geometría: nunca deformar", () => {
  const sources = [
    { width: 1920, height: 1080 },
    { width: 1080, height: 1920 },
    { width: 1440, height: 1080 },
    { width: 3840, height: 2160 },
    { width: 720, height: 720 },
  ];

  for (const format of Object.values(FORMATS)) {
    for (const source of sources) {
      it(`${source.width}×${source.height} → ${format.id}`, () => {
        const r = centeredCoverReframe(source, format);
        expect(reframeMatchesOutput(r, source, format)).toBe(true);
        const cover = placeReframe(r, source, format);
        // Mismo factor en ambos ejes: la proporción dibujada es la del original.
        expect(cover.width / cover.height).toBeCloseTo(source.width / source.height, 6);
        expect(cover.width).toBeGreaterThanOrEqual(format.width - 1e-6);
        expect(cover.height).toBeGreaterThanOrEqual(format.height - 1e-6);
        expect(cover.left).toBeLessThanOrEqual(1e-6);
        expect(cover.top).toBeLessThanOrEqual(1e-6);

        const contain = placeContain(source, format);
        expect(contain.width / contain.height).toBeCloseTo(source.width / source.height, 6);
        expect(contain.width).toBeLessThanOrEqual(format.width + 1e-6);
        expect(contain.height).toBeLessThanOrEqual(format.height + 1e-6);
      });
    }
  }
});

describe("composición: textos y subtítulos no se tapan", () => {
  it("reserva una banda inferior solo si hay subtítulos", async () => {
    const { subtitleBand } = await import("../compositions/Timeline");
    expect(subtitleBand(timelineSchema.parse(vertical([])))).toBe(0);
    const withSubs = timelineSchema.parse(
      vertical([{ id: "s", kind: "subtitles", size_px: 48, cues: [{ start_frame: 0, end_frame: 30, text: "Hola" }] }]),
    );
    // Dos líneas de 48 px con interlineado 1,2 + caja + separación.
    expect(subtitleBand(withSubs)).toBeGreaterThanOrEqual(48 * 1.2 * 2 + 20);
    const empty = timelineSchema.parse(vertical([{ id: "s", kind: "subtitles", cues: [] }]));
    expect(subtitleBand(empty)).toBe(0);
  });
});
