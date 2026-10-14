"use client";

import { useQuery } from "@tanstack/react-query";
import { PlayCircle } from "lucide-react";
import { useState } from "react";

import { Alert, Button, Card, KeyValues, SelectField, Spinner } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { keys, useInvalidate, useSystemStatus } from "@/lib/queries";

import styles from "./config.module.css";
import { JobDetailView } from "./JobDetailView";
import { RemotionPanel } from "./RemotionPanel";

const SELFTEST = "system.render_selftest";

export function SystemPanel({ canManage }: { canManage: boolean }) {
  const status = useSystemStatus();
  const invalidate = useInvalidate();
  const latest = useQuery({
    queryKey: ["jobs", "selftest-latest"],
    queryFn: () => unwrap(api.GET("/api/v1/jobs", { params: { query: { type: SELFTEST, limit: 1 } } })),
  });
  const [duration, setDuration] = useState("3");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function runSelftest() {
    setBusy(true);
    setError(null);
    try {
      await unwrap(api.POST("/api/v1/system/selftest", { body: { duration_s: Number(duration) } }));
      await invalidate(["jobs"], keys.status);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const latestJob = latest.data?.items[0];
  const s = status.data;

  return (
    <div className={styles.stack}>
      <div className={styles.twoCols}>
        <Card label="Servidor" title="Estado de servicios">
          {s ? (
            <KeyValues
              items={[
                ["Estado global", s.status],
                ["Versión", `${s.version} (${s.environment})`],
                ["Base de datos", `${s.checks.database?.status} · migración ${s.checks.database?.migration ?? "—"}`],
                ["Redis", s.checks.redis?.status ?? "—"],
                ["Almacenamiento", `${s.checks.storage?.status} · ${s.checks.storage?.bucket ?? "—"}`],
                ["ffprobe (API)", s.ffprobe.version ?? "no disponible"],
                ["IA", s.ai.configured ? `configurada (${s.ai.provider})` : "no configurada (modo manual)"],
                ["Hora del servidor", formatDateTime(s.server_time)],
              ]}
            />
          ) : status.isError ? (
            <Alert tone="error">{errorMessage(status.error)}</Alert>
          ) : (
            <Spinner />
          )}
        </Card>

        <Card
          label="Prueba técnica"
          title="Autotest de render"
          description="Un worker genera una señal sintética (barras y tono) en MP4 H.264/AAC 1080×1920 a 30 fps, la sube y el servidor la verifica con ffprobe. Comprueba la cadena completa sin usar material de DEKEN."
        >
          {canManage ? (
            <div className={styles.inlineForm}>
              <SelectField
                label="Duración"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                options={[
                  { value: "3", label: "3 segundos" },
                  { value: "10", label: "10 segundos" },
                  { value: "30", label: "30 segundos" },
                ]}
              />
              <Button variant="primary" onClick={runSelftest} busy={busy}>
                <PlayCircle size={16} aria-hidden="true" />
                Ejecutar autotest
              </Button>
            </div>
          ) : (
            <p className={styles.muted}>Solo los administradores pueden lanzar el autotest.</p>
          )}
          {error ? <Alert tone="error">{error}</Alert> : null}
          {s && s.workers.online === 0 ? (
            <Alert tone="info">
              No hay ningún worker en línea: el autotest quedará en cola hasta que se conecte uno
              (Configuración → Workers).
            </Alert>
          ) : null}
        </Card>
      </div>
      {latestJob ? <JobDetailView jobId={latestJob.id} canManage={canManage} /> : null}
      <RemotionPanel canManage={canManage} />
    </div>
  );
}
