export type { components, operations, paths } from "./api";

import type { components } from "./api";

export type Schemas = components["schemas"];
export type JobStatus = Schemas["JobStatus"];
export type Role = Schemas["Role"];
export type Permission = Schemas["Permission"];

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  queued: "En cola",
  processing: "Procesando",
  completed: "Completado",
  failed: "Fallido",
  cancelled: "Cancelado",
};

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Administración",
  editor: "Edición y producción",
  reviewer: "Revisión y aprobación",
  viewer: "Solo lectura",
};
