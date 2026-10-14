import {
  BarChart3,
  CalendarDays,
  Clapperboard,
  Film,
  FolderOpen,
  LayoutDashboard,
  type LucideIcon,
  Palette,
  Send,
  Settings,
  Sparkles,
} from "lucide-react";

import type { NavIcon as NavIconName } from "@/lib/nav";

const ICONS: Record<NavIconName, LucideIcon> = {
  dashboard: LayoutDashboard,
  director: Sparkles,
  library: FolderOpen,
  producer: Clapperboard,
  editor: Film,
  calendar: CalendarDays,
  brand: Palette,
  publications: Send,
  analytics: BarChart3,
  settings: Settings,
};

export function NavIcon({ name }: { name: NavIconName }) {
  const Icon = ICONS[name];
  return <Icon size={18} aria-hidden="true" />;
}
