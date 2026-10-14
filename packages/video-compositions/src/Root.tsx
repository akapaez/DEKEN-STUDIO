import { Composition } from "remotion";

import {
  EVALUATION_ID,
  EVALUATION_SECONDS,
  EvaluationComposition,
  evaluationDefaults,
} from "./compositions/Evaluation";
import { TIMELINE_ID, TimelineComposition, timelineMetadata } from "./compositions/Timeline";
import { emptyTimeline } from "./schema/timeline";
import { FORMATS, OUTPUT_FPS } from "./formats";

/** Registro de composiciones disponibles para el render (bundle de Remotion). */
export function RemotionRoot() {
  const v = FORMATS.vertical_9_16;
  return (
    <>
      <Composition
        id={EVALUATION_ID}
        component={EvaluationComposition}
        width={v.width}
        height={v.height}
        fps={OUTPUT_FPS}
        durationInFrames={EVALUATION_SECONDS * OUTPUT_FPS}
        defaultProps={evaluationDefaults}
      />
      <Composition
        id={TIMELINE_ID}
        component={TimelineComposition}
        width={v.width}
        height={v.height}
        fps={OUTPUT_FPS}
        durationInFrames={OUTPUT_FPS}
        defaultProps={{ timeline: emptyTimeline("vertical_9_16", 1), sources: {}, evaluation: true }}
        calculateMetadata={timelineMetadata}
      />
    </>
  );
}
