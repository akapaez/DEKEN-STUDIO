"use client";

import { JOB_STATUS_LABELS, type JobStatus } from "@deken/shared";
import Link from "next/link";

import { Alert, Badge, Card, EmptyState, JobStatusBadge, Spinner, Table, type Tone } from "@/components/ui";
import { formatDateTime, formatRelative, jobTypeLabel } from "@/lib/format";
import { NAV_ITEMS } from "@/lib/nav";
import { useJobs, useMe, useSystemStatus, type SystemStatus } from "@/lib/queries";

import styles from "./dashboard.module.css";

const STATUS_ORDER: JobStatus[] = ["queued", "processing", "completed", "failed", "cancelled"];

function Tile({
  label,
  value,
  tone,
  detail,
}: {
  label: string;
  value: string;
  tone: Tone;
  detail?: string;
}) {
  return (
    <div className={styles.tile}>
      <span className="label">{label}</span>
      <span className={styles.tileValue}>
        <Badge tone={tone}>{value}</Badge>
      </span>
      {detail ? <span className={styles.tileDetail}>{detail}</span> : null}
    </div>
  );
}

function checkTile(label: string, check: SystemStatus["checks"][string] | undefined, extra?: string) {
  const ok = check?.status === "ok";
  const detail = ok
    ? [check?.latency_ms !== null && check?.latency_ms !== undefined ? `${check.latency_ms} ms` : null, extra]
        .filter(Boolean)
        .join(" · ")
    : `Error: ${check?.error ?? "sin respuesta"}`;
  return <Tile label={label} value={ok ? "Operativo" : "Caído"} tone={ok ? "ok" : "error"} detail={detail} />;
}

function StatusTiles({ status }: { status: SystemStatus }) {
  const { checks, workers, ai, ffprobe } = status;
  return (
    <div className={styles.grid}>
      <Tile
        label="Plataforma"
        value={status.status === "ok" ? "Operativa" : status.status === "degraded" ? "Degradada" : "Con errores"}
        tone={status.status === "ok" ? "ok" : status.status === "degraded" ? "warning" : "error"}
        detail={`v${status.version} · ${status.environment}`}
      />
      {checkTile("Base de datos", checks.database, checks.database?.migration ? `migración ${checks.database.migration}` : undefined)}
      {checkTile("Cola (Redis)", checks.redis)}
      {checkTile("Almacenamiento", checks.storage, checks.storage?.bucket ?? undefined)}
      <Tile
        label="Workers en línea"
        value={`${workers.online} de ${workers.active}`}
        tone={workers.online > 0 ? "ok" : "warning"}
        detail={
          workers.online > 0
            ? workers.online_names.join(", ")
            : "Ningún worker conectado: los trabajos esperarán en cola."
        }
      />
      <Tile
        label="Verificación de vídeo"
        value={ffprobe.available ? "Disponible" : "No disponible"}
        tone={ffprobe.available ? "ok" : "error"}
        detail={ffprobe.version ? `ffprobe ${ffprobe.version}` : "ffprobe no encontrado en el servidor"}
      />
      <Tile
        label="Proveedor de IA"
        value={ai.configured ? "Configurado" : "No configurado"}
        tone={ai.configured ? "ok" : "muted"}
        detail={
          ai.configured
            ? `Proveedor: ${ai.provider}`
            : "Sin clave de IA. El Director IA (Sprint 2) funcionará en modo manual hasta configurarla."
        }
      />
    </div>
  );
}

export function Dashboard() {
  const me = useMe();
  const status = useSystemStatus();
  const jobs = useJobs(undefined, 8);
  const available = NAV_ITEMS.filter((i) => i.href !== null);
  const upcoming = NAV_ITEMS.filter((i) => i.href === null);

  return (
    <>
      <header className={styles.header}>
        <span className="label">Dashboard</span>
        <h1>Hola, {me.data?.user.full_name.split(" ")[0]}</h1>
        <p className={styles.subtitle}>Estado real de la plataforma y del procesamiento audiovisual.</p>
      </header>

      {status.isPending ? (
        <Spinner label="Cargando estado" />
      ) : status.isError ? (
        <Alert tone="error">No se pudo obtener el estado del sistema: {status.error.message}</Alert>
      ) : (
        <StatusTiles status={status.data} />
      )}

      <div className={styles.columns}>
        <Card
          label="Procesamiento"
          title="Trabajos recientes"
          actions={<Link href="/configuracion?tab=trabajos">Ver todos</Link>}
        >
          {status.data ? (
            <div className={styles.counts}>
              {STATUS_ORDER.map((s) => (
                <div key={s} className={styles.count}>
                  <span className="label">{JOB_STATUS_LABELS[s]}</span>
                  <span className={styles.countValue}>{status.data.jobs.by_status[s] ?? 0}</span>
                </div>
              ))}
            </div>
          ) : null}
          {jobs.data && jobs.data.items.length > 0 ? (
            <Table caption="Trabajos recientes">
              <thead>
                <tr>
                  <th scope="col">Tipo</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Creado</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.items.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <Link href={`/configuracion?tab=trabajos&job=${job.id}`}>{jobTypeLabel(job.type)}</Link>
                    </td>
                    <td>
                      <JobStatusBadge status={job.status} />
                    </td>
                    <td title={formatDateTime(job.created_at)}>{formatRelative(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : jobs.isPending ? (
            <Spinner />
          ) : (
            <EmptyState title="Todavía no hay trabajos">
              Un administrador puede lanzar el autotest de render desde Configuración → Sistema para
              comprobar la cadena completa.
            </EmptyState>
          )}
        </Card>

        <Card label="Producto" title="Disponibilidad de secciones" description="La plataforma se entrega por sprints con criterios verificables.">
          <ul className={styles.roadmap}>
            {available.map((item) => (
              <li key={item.id}>
                <span>{item.label}</span>
                <Badge tone="ok">Disponible</Badge>
              </li>
            ))}
            {upcoming.map((item) => (
              <li key={item.id}>
                <span>{item.label}</span>
                <Badge tone="muted">{item.availability}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
