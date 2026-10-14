"use client";

import { ROLE_LABELS } from "@deken/shared";
import { LogOut } from "lucide-react";
import type { Route } from "next";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { ApiError } from "@/lib/api";
import { NAV_ITEMS, isActive } from "@/lib/nav";
import { useLogout, useMe } from "@/lib/queries";

import styles from "./AppShell.module.css";
import { NavIcon } from "./NavIcon";
import { ThemeToggle } from "./ThemeToggle";
import { Alert, Button, Spinner } from "./ui";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const me = useMe();
  const logout = useLogout();

  const unauthenticated = me.error instanceof ApiError && me.error.status === 401;
  useEffect(() => {
    if (unauthenticated) {
      const next = pathname === "/" ? "" : `?next=${encodeURIComponent(pathname)}`;
      router.replace(`/login${next}` as Route);
    }
  }, [unauthenticated, pathname, router]);

  if (me.isPending || unauthenticated) {
    return (
      <div className={styles.loading}>
        <Spinner label="Comprobando la sesión" />
      </div>
    );
  }
  if (me.isError) {
    return (
      <div className={styles.loading}>
        <Alert tone="error">No se puede contactar con la API: {me.error.message}</Alert>
      </div>
    );
  }

  const user = me.data.user;
  return (
    <div className={styles.shell}>
      <a href="#contenido" className={styles.skip}>
        Saltar al contenido
      </a>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.wordmark}>
            DEKEN <span>STUDIO AI</span>
          </span>
          <span className="label">Grupo Deken · Uso interno</span>
        </div>
        <nav className={styles.nav} aria-label="Secciones">
          <ul>
            {NAV_ITEMS.map((item) => {
              const active = isActive(item, pathname);
              if (item.href === null) {
                return (
                  <li key={item.id}>
                    <span
                      className={`${styles.navItem} ${styles.navDisabled}`}
                      aria-disabled="true"
                      title={`${item.description}. Disponible en ${item.availability}.`}
                    >
                      <NavIcon name={item.icon} />
                      <span className={styles.navLabel}>{item.label}</span>
                      <span className={styles.soon}>{item.availability}</span>
                    </span>
                  </li>
                );
              }
              return (
                <li key={item.id}>
                  <Link
                    href={item.href}
                    className={`${styles.navItem} ${active ? styles.navActive : ""}`}
                    aria-current={active ? "page" : undefined}
                    title={item.description}
                  >
                    <NavIcon name={item.icon} />
                    <span className={styles.navLabel}>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <p className={styles.sidebarFooter}>
          Las secciones marcadas con sprint aún no están disponibles. Ver el plan de implementación.
        </p>
      </aside>
      <div className={styles.main}>
        <header className={styles.topbar}>
          <ThemeToggle />
          <div className={styles.user}>
            <span className={styles.userName}>{user.full_name}</span>
            <span className="label">{ROLE_LABELS[user.role]}</span>
          </div>
          <Button variant="ghost" size="small" onClick={() => logout.mutate()} busy={logout.isPending}>
            <LogOut size={16} aria-hidden="true" />
            Salir
          </Button>
        </header>
        <main id="contenido" className={styles.content} tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
