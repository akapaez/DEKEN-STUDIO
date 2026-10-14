import { describe, expect, it } from "vitest";

import { brand, contrastRatio, neutralsDark, neutralsLight, onGreen, status } from "./index";

describe("paleta de marca", () => {
  it("prohíbe texto blanco sobre verde (contraste insuficiente)", () => {
    expect(contrastRatio("#FFFFFF", brand.green)).toBeLessThan(3);
    expect(contrastRatio(onGreen, brand.green)).toBeGreaterThanOrEqual(7);
  });

  it.each([
    ["oscuro", neutralsDark],
    ["claro", neutralsLight],
  ])("tema %s: texto legible (WCAG AA) sobre fondo y superficies", (_, n) => {
    for (const bg of [n.background, n.surface, n.surfaceRaised]) {
      expect(contrastRatio(n.text, bg)).toBeGreaterThanOrEqual(7);
      expect(contrastRatio(n.textSecondary, bg)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(n.label, bg)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("el verde como acento se lee sobre el fondo oscuro de marca", () => {
    expect(contrastRatio(brand.green, neutralsDark.background)).toBeGreaterThanOrEqual(7);
  });

  it("los colores de estado cumplen AA en su tema", () => {
    expect(contrastRatio(status.dangerDark, neutralsDark.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(status.dangerLight, neutralsLight.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(status.warningDark, neutralsDark.surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(status.warningLight, neutralsLight.surface)).toBeGreaterThanOrEqual(4.5);
  });
});
