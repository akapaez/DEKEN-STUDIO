"use client";

import type { Permission } from "@deken/shared";
import type { Route } from "next";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { useMe } from "@/lib/queries";

import { AccountPanel } from "./AccountPanel";
import { AuditPanel } from "./AuditPanel";
import styles from "./config.module.css";
import { JobsPanel } from "./JobsPanel";
import { SystemPanel } from "./SystemPanel";
import { UsersPanel } from "./UsersPanel";
import { WorkersPanel } from "./WorkersPanel";

interface TabDef {
  id: string;
  label: string;
  permission?: Permission;
}

export const TABS: TabDef[] = [
  { id: "sistema", label: "Sistema" },
  { id: "trabajos", label: "Trabajos", permission: "jobs:read" },
  { id: "workers", label: "Workers" },
  { id: "usuarios", label: "Usuarios", permission: "users:manage" },
  { id: "auditoria", label: "Auditoría", permission: "audit:read" },
  { id: "cuenta", label: "Mi cuenta" },
];

export function ConfigPage() {
  const params = useSearchParams();
  const me = useMe();
  const permissions = new Set(me.data?.permissions ?? []);
  const visible = TABS.filter((t) => !t.permission || permissions.has(t.permission));
  const requested = params.get("tab") ?? "sistema";
  const current = visible.find((t) => t.id === requested) ?? visible[0];
  const can = (p: Permission) => permissions.has(p);

  return (
    <>
      <header className={styles.header}>
        <span className="label">Configuración</span>
        <h1>Sistema y administración</h1>
      </header>
      <nav aria-label="Apartados de configuración" className={styles.tabs}>
        {visible.map((tab) => (
          <Link
            key={tab.id}
            href={`/configuracion?tab=${tab.id}` as Route}
            className={`${styles.tab} ${tab.id === current?.id ? styles.tabActive : ""}`}
            aria-current={tab.id === current?.id ? "page" : undefined}
          >
            {tab.label}
          </Link>
        ))}
      </nav>
      {current?.id === "sistema" && <SystemPanel canManage={can("system:manage")} />}
      {current?.id === "trabajos" && <JobsPanel canManage={can("jobs:manage")} initialJob={params.get("job")} />}
      {current?.id === "workers" && <WorkersPanel canManage={can("workers:manage")} />}
      {current?.id === "usuarios" && <UsersPanel currentUserId={me.data?.user.id ?? ""} />}
      {current?.id === "auditoria" && <AuditPanel />}
      {current?.id === "cuenta" && <AccountPanel />}
    </>
  );
}
