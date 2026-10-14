import type { Tone } from "@/components/ui";

export const MEDIA_STATUS: Record<string, { label: string; tone: Tone }> = {
  uploading: { label: "Subiendo", tone: "active" },
  processing: { label: "Procesando", tone: "active" },
  ready: { label: "Lista", tone: "ok" },
  rejected: { label: "Rechazada", tone: "error" },
  failed: { label: "Error de proceso", tone: "error" },
  duplicate: { label: "Duplicada", tone: "warning" },
  cancelled: { label: "Cancelada", tone: "muted" },
};

export const ORIENTATION: Record<string, string> = {
  vertical: "Vertical",
  horizontal: "Horizontal",
  square: "Cuadrada",
};

export const PEOPLE: Record<string, string> = {
  unknown: "Sin revisar",
  yes: "Aparecen personas",
  no: "No aparecen personas",
};

export const CONSENT: Record<string, { label: string; tone: Tone }> = {
  not_required: { label: "No requerido", tone: "ok" },
  pending: { label: "Pendiente", tone: "warning" },
  granted: { label: "Concedido", tone: "ok" },
  denied: { label: "Denegado", tone: "error" },
};

export function statusOf(status: string) {
  return MEDIA_STATUS[status] ?? { label: status, tone: "muted" as Tone };
}
