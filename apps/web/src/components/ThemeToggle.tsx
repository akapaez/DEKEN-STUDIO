"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

import {
  THEME_LABELS,
  applyThemePreference,
  nextThemePreference,
  readThemePreference,
  type ThemePreference,
} from "@/lib/theme";

import { Button } from "./ui";

const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};
const getServerSnapshot = (): ThemePreference => "system";

export function ThemeToggle() {
  const preference = useSyncExternalStore(subscribe, readThemePreference, getServerSnapshot);
  const next = nextThemePreference(preference);
  const Icon = preference === "light" ? Sun : preference === "dark" ? Moon : Monitor;
  return (
    <Button
      variant="ghost"
      size="small"
      onClick={() => {
        applyThemePreference(next);
        listeners.forEach((l) => l());
      }}
      aria-label={`${THEME_LABELS[preference]}. Cambiar a ${THEME_LABELS[next].toLowerCase()}`}
      title={`Cambiar a ${THEME_LABELS[next].toLowerCase()}`}
    >
      <Icon size={16} aria-hidden="true" />
      <span>{THEME_LABELS[preference]}</span>
    </Button>
  );
}
