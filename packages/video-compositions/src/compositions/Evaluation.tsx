/**
 * Composición de EVALUACIÓN técnica de Remotion (5 s, 1080×1920, 30 fps).
 *
 * Solo recursos sintéticos/corporativos autorizados: fondo gris DEKEN, título animado,
 * línea verde y un barrido verde como transición. No usa grabaciones ni logos y no es
 * una pieza comercial: lleva la etiqueta "EVALUACIÓN TÉCNICA".
 */
import { brand, neutralsDark } from "@deken/brand";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";

import { ArrivingText, BrandBackground, GreenRule, GreenWipe, Label, SafeArea } from "../components/primitives";
import { ensureBrandFonts } from "../fonts";
import { FORMATS } from "../formats";
import { type EvaluationProps, evaluationPropsSchema } from "../schema/evaluation";

export { EVALUATION_ID, EVALUATION_SECONDS, evaluationDefaults, evaluationPropsSchema } from "../schema/evaluation";
export type { EvaluationProps } from "../schema/evaluation";

/** Fotogramas clave (a 30 fps) de la composición. */
export const EVALUATION_TIMING = {
  wipeStart: 72,
  wipeFrames: 16,
  secondScene: 80,
  finalHoldFrames: 36,
} as const;

export function EvaluationComposition(props: EvaluationProps) {
  ensureBrandFonts();
  const { title, subtitle, label } = evaluationPropsSchema.parse(props);
  const { width, durationInFrames } = useVideoConfig();
  const safe = FORMATS.vertical_9_16.safe;
  const t = EVALUATION_TIMING;
  return (
    <AbsoluteFill>
      <BrandBackground color={brand.gray} push={0.04}>
        <Sequence durationInFrames={t.secondScene}>
          <SafeArea {...safe}>
            <Label start={0}>{label}</Label>
            <ArrivingText size={132} start={4}>
              {title}
            </ArrivingText>
            <GreenRule start={12} width={width * 0.55} />
          </SafeArea>
        </Sequence>
        <Sequence from={t.secondScene} durationInFrames={durationInFrames - t.secondScene}>
          <SafeArea {...safe}>
            <Label start={4}>Remotion · 1080×1920 · 30 fps</Label>
            <ArrivingText size={104} start={8} weight={800}>
              {subtitle}
            </ArrivingText>
            <ArrivingText size={44} start={18} weight={700} color={neutralsDark.textSecondary}>
              Fondo gris DEKEN · línea verde · barrido
            </ArrivingText>
            <GreenRule start={22} width={width * 0.3} />
          </SafeArea>
        </Sequence>
      </BrandBackground>
      <GreenWipe start={t.wipeStart} duration={t.wipeFrames} />
    </AbsoluteFill>
  );
}
