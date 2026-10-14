/**
 * Navegación principal. Las secciones aún no implementadas se muestran deshabilitadas
 * con el sprint en el que llegan: nunca se presentan como operativas.
 */

export type NavIcon =
  | "dashboard"
  | "director"
  | "library"
  | "producer"
  | "editor"
  | "calendar"
  | "brand"
  | "publications"
  | "analytics"
  | "settings";

export interface NavItem {
  id: string;
  label: string;
  icon: NavIcon;
  /** Ruta si la sección está disponible; null si aún no lo está. */
  href: "/" | "/configuracion" | null;
  /** Cuándo llega la sección (solo si no está disponible). */
  availability?: string;
  description: string;
}

export const NAV_ITEMS: readonly NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard", href: "/", description: "Estado del sistema y actividad" },
  { id: "director", label: "Director IA", icon: "director", href: null, availability: "Sprint 2", description: "Estrategias, campañas y guiones con fuentes verificadas" },
  { id: "library", label: "Biblioteca", icon: "library", href: null, availability: "Sprint 1", description: "Grabaciones reales de DEKEN, metadatos y previsualizaciones" },
  { id: "producer", label: "Productor audiovisual", icon: "producer", href: null, availability: "Sprint 3", description: "Segmentos, propuesta de montaje y render" },
  { id: "editor", label: "Editor", icon: "editor", href: null, availability: "Sprint 4", description: "Línea de tiempo, reencuadre y subtítulos" },
  { id: "calendar", label: "Calendario", icon: "calendar", href: null, availability: "Sprint 2", description: "Calendario editorial y campañas" },
  { id: "brand", label: "Marca DEKEN", icon: "brand", href: null, availability: "Sprint 1", description: "Logos oficiales, tipografías y reglas de marca" },
  { id: "publications", label: "Publicaciones", icon: "publications", href: null, availability: "V2", description: "Publicación con APIs oficiales y aprobación humana" },
  { id: "analytics", label: "Analítica y leads", icon: "analytics", href: null, availability: "V2", description: "Estadísticas de contenidos y captación comercial" },
  { id: "settings", label: "Configuración", icon: "settings", href: "/configuracion", description: "Sistema, usuarios, workers, trabajos y auditoría" },
];

export function isActive(item: NavItem, pathname: string): boolean {
  if (item.href === null) return false;
  if (item.href === "/") return pathname === "/";
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}
