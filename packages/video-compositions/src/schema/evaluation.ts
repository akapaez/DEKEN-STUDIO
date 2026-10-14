/** Propiedades de la composición de evaluación técnica (sin dependencias de React). */
import { z } from "zod";

export const EVALUATION_ID = "DekenEvaluation";
export const EVALUATION_SECONDS = 5;

export const evaluationPropsSchema = z
  .object({
    title: z.string().min(1).max(40).default("DEKEN STUDIO AI"),
    subtitle: z.string().min(1).max(60).default("Motor de composición"),
    label: z.string().min(1).max(40).default("Evaluación técnica"),
  })
  .strict();

export type EvaluationProps = z.infer<typeof evaluationPropsSchema>;

export const evaluationDefaults: EvaluationProps = evaluationPropsSchema.parse({});
