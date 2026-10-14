export type ThemePreference = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "deken-theme";

/** Script mínimo que se ejecuta antes de pintar (con nonce de CSP). */
export const THEME_BOOTSTRAP_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t==="light"||t==="dark"){document.documentElement.dataset.theme=t;}}catch(e){}})();`;

export function readThemePreference(): ThemePreference {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

export function applyThemePreference(preference: ThemePreference): void {
  const root = document.documentElement;
  if (preference === "system") {
    delete root.dataset.theme;
  } else {
    root.dataset.theme = preference;
  }
  try {
    if (preference === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
    else window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    // Almacenamiento no disponible: el tema se aplica solo a esta sesión.
  }
}

export function nextThemePreference(current: ThemePreference): ThemePreference {
  return current === "system" ? "light" : current === "light" ? "dark" : "system";
}

export const THEME_LABELS: Record<ThemePreference, string> = {
  system: "Tema del sistema",
  light: "Tema claro",
  dark: "Tema oscuro",
};
