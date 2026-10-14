import { z } from "zod";

import { TIMELINE_SCHEMA_ID, timelineSchema } from "../src/schema/timeline";

export function timelineJsonSchema(): Record<string, unknown> {
  const schema = z.toJSONSchema(timelineSchema, { io: "input", unrepresentable: "any" }) as Record<string, unknown>;
  return {
    ...schema,
    $id: `https://deken.studio/schemas/${TIMELINE_SCHEMA_ID.replace("/", "-")}.json`,
    title: "Línea de tiempo DEKEN v1",
    description:
      "GENERADO desde packages/video-compositions/src/schema/timeline.ts (zod). No editar a mano. " +
      "Las reglas semánticas (solapes, zonas seguras, logos, licencias) están en validate.ts.",
  };
}
