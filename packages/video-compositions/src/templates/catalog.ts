/**
 * Catálogo de plantillas audiovisuales DEKEN.
 *
 * Una plantilla NO es un vídeo: es la estructura editable (formato, tramos, estilos de
 * texto y reglas) a partir de la cual el productor (Sprint 3) propone una línea de
 * tiempo con planos REALES de la biblioteca. Si falta un plano, la propuesta lo marca
 * como "pendiente de grabar": nunca se inventa una escena.
 */
import type { FormatId } from "../formats";

export type SlotKind = "footage" | "text" | "brand_outro" | "brand_intro";

export interface TemplateSlot {
  id: string;
  kind: SlotKind;
  label: string;
  /** Qué debe mostrar el plano (orienta la búsqueda en la biblioteca). */
  guidance: string;
  min_seconds: number;
  max_seconds: number;
  text_style?: "headline" | "title" | "body" | "label";
}

export interface TemplateDefinition {
  id: string;
  name: string;
  purpose: string;
  formats: FormatId[];
  duration_seconds: { min: number; max: number };
  transitions: Array<"cut" | "fade" | "wipe">;
  subtitles: "required" | "recommended" | "optional";
  slots: TemplateSlot[];
}

const footage = (id: string, label: string, guidance: string, min: number, max: number): TemplateSlot => ({
  id,
  kind: "footage",
  label,
  guidance,
  min_seconds: min,
  max_seconds: max,
});

const text = (
  id: string,
  label: string,
  guidance: string,
  style: TemplateSlot["text_style"],
  min = 2.5,
  max = 6,
): TemplateSlot => ({ id, kind: "text", label, guidance, min_seconds: min, max_seconds: max, text_style: style });

const outro: TemplateSlot = {
  id: "cierre",
  kind: "brand_outro",
  label: "Cierre de marca",
  guidance: "Logo oficial sobre fondo de marca y llamada a la acción para profesionales",
  min_seconds: 2,
  max_seconds: 4,
};

export const TEMPLATES: TemplateDefinition[] = [
  {
    id: "reel_vertical",
    name: "Reel vertical",
    purpose: "Pieza corta para Reels/Shorts/TikTok con gancho en el primer segundo",
    formats: ["vertical_9_16"],
    duration_seconds: { min: 8, max: 60 },
    transitions: ["cut", "wipe"],
    subtitles: "required",
    slots: [
      footage("gancho", "Gancho", "El momento más llamativo del proceso, grande y legible desde el fotograma 0", 1, 3),
      text("idea", "Idea principal", "Una sola idea por plano", "headline"),
      footage("desarrollo", "Desarrollo", "Planos reales que demuestran la idea", 4, 30),
      outro,
    ],
  },
  {
    id: "horizontal_16_9",
    name: "Vídeo horizontal",
    purpose: "YouTube, LinkedIn y web",
    formats: ["horizontal_16_9"],
    duration_seconds: { min: 20, max: 300 },
    transitions: ["cut", "fade"],
    subtitles: "recommended",
    slots: [
      text("titulo", "Título", "Qué va a ver el profesional", "title"),
      footage("cuerpo", "Cuerpo", "Secuencia principal", 15, 280),
      outro,
    ],
  },
  {
    id: "square_post",
    name: "Publicación cuadrada",
    purpose: "Feed 1:1 con mensaje directo",
    formats: ["square_1_1"],
    duration_seconds: { min: 6, max: 45 },
    transitions: ["cut"],
    subtitles: "required",
    slots: [footage("plano", "Plano principal", "Producto o proceso centrado", 4, 40), text("mensaje", "Mensaje", "Frase corta", "headline"), outro],
  },
  {
    id: "educational",
    name: "Vídeo educativo",
    purpose: "Explicar un concepto técnico con pasos numerados",
    formats: ["vertical_9_16", "horizontal_16_9"],
    duration_seconds: { min: 20, max: 180 },
    transitions: ["cut", "fade"],
    subtitles: "required",
    slots: [
      text("pregunta", "Pregunta", "La duda real del instalador", "title"),
      footage("paso_1", "Paso 1", "Plano real del primer paso", 3, 30),
      footage("paso_2", "Paso 2", "Plano real del segundo paso", 3, 30),
      footage("paso_3", "Paso 3", "Plano real del tercer paso", 3, 30),
      text("resumen", "Resumen", "Lo que hay que recordar", "body"),
      outro,
    ],
  },
  {
    id: "industrial_process",
    name: "Proceso industrial",
    purpose: "Mostrar una fase de fabricación tal como ocurre en la fábrica de Santiponce",
    formats: ["vertical_9_16", "horizontal_16_9", "square_1_1"],
    duration_seconds: { min: 10, max: 120 },
    transitions: ["cut"],
    subtitles: "recommended",
    slots: [
      footage("maquina", "Máquina o puesto", "Plano general del puesto real; el proceso debe verse completo", 3, 20),
      footage("detalle", "Detalle", "Primer plano de la operación (sin recortar la parte relevante)", 3, 30),
      text("dato", "Dato verificado", "Solo datos de la base de conocimiento", "label"),
      outro,
    ],
  },
  {
    id: "product_showcase",
    name: "Presentación de producto",
    purpose: "Presentar un sistema de ventana o puerta fabricado por DEKEN",
    formats: ["vertical_9_16", "horizontal_16_9", "square_1_1"],
    duration_seconds: { min: 10, max: 90 },
    transitions: ["cut", "fade"],
    subtitles: "recommended",
    slots: [
      footage("producto", "Producto", "Producto terminado real", 3, 20),
      text("nombre", "Nombre del sistema", "Nombre comercial exacto", "title"),
      footage("detalles", "Detalles", "Herrajes, perfiles, acabados reales", 4, 40),
      outro,
    ],
  },
  {
    id: "b2b_commercial",
    name: "Comercial B2B",
    purpose: "Captar instaladores, distribuidores y constructoras (no particulares)",
    formats: ["vertical_9_16", "horizontal_16_9"],
    duration_seconds: { min: 15, max: 60 },
    transitions: ["cut", "wipe"],
    subtitles: "required",
    slots: [
      text("problema", "Problema del profesional", "Plazos, calidad, suministro", "headline"),
      footage("solucion", "Solución DEKEN", "Fábrica, logística o producto reales", 6, 40),
      text("cta", "Llamada a la acción", "Contacto profesional", "title"),
      outro,
    ],
  },
  {
    id: "technical_comparison",
    name: "Comparación técnica",
    purpose: "Comparar dos opciones con una escala compartida",
    formats: ["horizontal_16_9", "vertical_9_16"],
    duration_seconds: { min: 15, max: 90 },
    transitions: ["cut"],
    subtitles: "required",
    slots: [
      text("criterio", "Criterio", "Qué se compara y con qué unidad", "title"),
      footage("opcion_a", "Opción A", "Plano real de la opción A", 3, 30),
      footage("opcion_b", "Opción B", "Plano real de la opción B", 3, 30),
      text("conclusion", "Conclusión", "Solo con datos verificados", "body"),
      outro,
    ],
  },
  {
    id: "brand_animation",
    name: "Animación de marca",
    purpose: "Pieza gráfica sin metraje con colores y tipografía de marca",
    formats: ["vertical_9_16", "horizontal_16_9", "square_1_1"],
    duration_seconds: { min: 4, max: 20 },
    transitions: ["wipe"],
    subtitles: "optional",
    slots: [text("mensaje", "Mensaje", "Una idea por plano", "headline", 2.5, 8), outro],
  },
  {
    id: "corporate_intro_outro",
    name: "Intro y cierre corporativos",
    purpose: "Apertura y cierre reutilizables para cualquier pieza",
    formats: ["vertical_9_16", "horizontal_16_9", "square_1_1"],
    duration_seconds: { min: 3, max: 8 },
    transitions: ["wipe"],
    subtitles: "optional",
    slots: [
      {
        id: "intro",
        kind: "brand_intro",
        label: "Intro",
        guidance: "Nombre de la pieza; el logo no aparece en los 3 primeros segundos del vídeo final",
        min_seconds: 1.5,
        max_seconds: 3,
      },
      outro,
    ],
  },
];

export function templateById(id: string): TemplateDefinition | undefined {
  return TEMPLATES.find((t) => t.id === id);
}
