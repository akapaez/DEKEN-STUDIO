"use client";

import { evaluationDefaults } from "@deken/video-compositions";
import { useQuery } from "@tanstack/react-query";
import { Clapperboard } from "lucide-react";
import dynamic from "next/dynamic";
import { useState } from "react";

import { Alert, Badge, Button, Card, Field, KeyValues, Spinner } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { keys, useInvalidate, useRenderEngine } from "@/lib/queries";

import styles from "./config.module.css";
import { JobDetailView } from "./JobDetailView";

const EVAL = "system.remotion_eval";

const RemotionPreview = dynamic(() => import("./RemotionPreview"), {
  ssr: false,
  loading: () => <Spinner label="Cargando la previsualización" />,
});

export function RemotionPanel({ canManage }: { canManage: boolean }) {
  const engine = useRenderEngine();
  const invalidate = useInvalidate();
  const latest = useQuery({
    queryKey: ["jobs", "remotion-latest"],
    queryFn: () => unwrap(api.GET("/api/v1/jobs", { params: { query: { type: EVAL, limit: 1 } } })),
  });
  const [title, setTitle] = useState(evaluationDefaults.title);
  const [subtitle, setSubtitle] = useState(evaluationDefaults.subtitle);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const props = {
    title: title.trim() || evaluationDefaults.title,
    subtitle: subtitle.trim() || evaluationDefaults.subtitle,
    label: evaluationDefaults.label,
  };

  async function render() {
    setBusy(true);
    setError(null);
    try {
      await unwrap(api.POST("/api/v1/renders/evaluation", { body: { title: props.title, subtitle: props.subtitle } }));
      await invalidate(["jobs"], keys.status);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const e = engine.data;
  const latestJob = latest.data?.items[0];

  return (
    <div className={styles.stack}>
      <div className={styles.twoCols}>
        <Card
          label="Motor de composición"
          title="Remotion"
          description="Motor principal de composición y render (títulos, transiciones, subtítulos, marca). FFmpeg queda para análisis, proxys y verificación."
          actions={
            e ? (
              e.commercial_renders_enabled ? (
                <Badge tone="ok">Licencia de empresa</Badge>
              ) : (
                <Badge tone="warning">Solo evaluación</Badge>
              )
            ) : null
          }
        >
          {e ? (
            <>
              <KeyValues
                items={[
                  ["Licencia", e.license_mode === "company" ? "empresa (verificada)" : "evaluación"],
                  ["Renders comerciales", e.commercial_renders_enabled ? "habilitados" : "deshabilitados"],
                  [
                    "Workers con Remotion",
                    e.workers_with_remotion.length ? e.workers_with_remotion.join(", ") : "ninguno en línea",
                  ],
                ]}
              />
              <Alert tone={e.commercial_renders_enabled ? "success" : "info"}>{e.note}</Alert>
            </>
          ) : engine.isError ? (
            <Alert tone="error">{errorMessage(engine.error)}</Alert>
          ) : (
            <Spinner />
          )}
        </Card>

        <Card
          label="Prueba técnica"
          title="Render de evaluación"
          description="5 s a 1080×1920 y 30 fps: fondo gris DEKEN, título animado, línea verde y transición. Sin material de DEKEN; sale con marca de agua de evaluación y se guarda aparte del contenido comercial."
        >
          <div className={styles.remotionGrid}>
            <div className={styles.playerBox}>
              <RemotionPreview props={props} />
              <span className="label">Previsualización (Remotion Player)</span>
            </div>
            <div className={styles.stack}>
              <Field label="Título" value={title} onChange={(ev) => setTitle(ev.target.value)} maxLength={40} />
              <Field label="Subtítulo" value={subtitle} onChange={(ev) => setSubtitle(ev.target.value)} maxLength={60} />
              <p className={styles.muted}>
                La previsualización y el render usan la misma composición (@deken/video-compositions).
              </p>
              {canManage ? (
                <div>
                  <Button variant="primary" onClick={render} busy={busy}>
                    <Clapperboard size={16} aria-hidden="true" />
                    Renderizar con Remotion
                  </Button>
                </div>
              ) : (
                <p className={styles.muted}>Solo los administradores pueden lanzar renders de evaluación.</p>
              )}
              {error ? <Alert tone="error">{error}</Alert> : null}
              {e && e.workers_with_remotion.length === 0 ? (
                <Alert tone="info">
                  Ningún worker en línea tiene Remotion: el render quedará en cola hasta que se conecte uno.
                </Alert>
              ) : null}
            </div>
          </div>
        </Card>
      </div>
      {latestJob ? <JobDetailView jobId={latestJob.id} canManage={canManage} /> : null}
    </div>
  );
}
