// Punto de entrada del bundle de Remotion (render en workers y Remotion Studio).
import "./fonts-files";

import { registerRoot } from "remotion";

import { RemotionRoot } from "./Root";

registerRoot(RemotionRoot);
