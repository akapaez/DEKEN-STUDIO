"use client";

import {
  EVALUATION_SECONDS,
  EvaluationComposition,
  FORMATS,
  OUTPUT_FPS,
  type EvaluationProps,
} from "@deken/video-compositions";
import { Player } from "@remotion/player";

import styles from "./config.module.css";

const VERTICAL = FORMATS.vertical_9_16;

/**
 * Previsualización en el navegador con Remotion Player de la MISMA composición que
 * renderiza el worker (@deken/video-compositions). Solo para evaluación técnica.
 */
export default function RemotionPreview({ props }: { props: EvaluationProps }) {
  return (
    <Player
      component={EvaluationComposition}
      inputProps={props}
      durationInFrames={EVALUATION_SECONDS * OUTPUT_FPS}
      fps={OUTPUT_FPS}
      compositionWidth={VERTICAL.width}
      compositionHeight={VERTICAL.height}
      className={styles.player}
      style={{ width: "100%" }}
      // Fotograma inicial con el título ya compuesto (la llegada empieza en el fotograma 4).
      initialFrame={45}
      controls
      loop
    />
  );
}
