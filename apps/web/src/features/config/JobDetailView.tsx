"use client";

import { Download } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Alert, Button, Card, JobStatusBadge, KeyValues, ProgressBar, Spinner } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { formatBytes, formatDateTime, formatDuration, formatPercent, jobTypeLabel, shortId } from "@/lib/format";
import { isTerminal, keys, useInvalidate, useJob, type JobDetail } from "@/lib/queries";

import styles from "./config.module.css";

type Output = JobDetail["outputs"][number];

interface StreamInfo {
  codec_type?: string;
  codec_name?: string;
  width?: number;
  height?: number;
  avg_frame_rate?: number;
  nb_frames?: number;
  sample_rate?: number;
  pix_fmt?: string;
}

function mediaSummary(output: Output): Array<[string, string]> {
  const info = output.stored_object.media_info as { duration_s?: number; streams?: StreamInfo[] } | null;
  const streams = info?.streams ?? [];
  const video = streams.find((s) => s.codec_type === "video");
  const audio = streams.find((s) => s.codec_type === "audio");
  const rows: Array<[string, string]> = [];
  if (video) {
    rows.push(["Vídeo", `${video.codec_name} · ${video.width}×${video.height} · ${video.pix_fmt ?? ""}`]);
    rows.push(["Fotogramas", `${video.nb_frames} a ${video.avg_frame_rate} fps`]);
  }
  if (audio) rows.push(["Audio", `${audio.codec_name} · ${audio.sample_rate} Hz`]);
  if (info?.duration_s !== undefined) rows.push(["Duración", formatDuration(info.duration_s)]);
  rows.push(["Tamaño", formatBytes(output.stored_object.size_bytes)]);
  if (output.stored_object.sha256) rows.push(["SHA-256", `${output.stored_object.sha256.slice(0, 16)}…`]);
  return rows;
}

function VideoOutput({ output, synthetic }: { output: Output; synthetic: boolean }) {
  const objectId = output.stored_object.id;
  const link = useQuery({
    queryKey: ["download-url", objectId],
    queryFn: () =>
      unwrap(api.GET("/api/v1/files/{object_id}/download-url", { params: { path: { object_id: objectId } } })),
    staleTime: 4 * 60_000,
  });
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function download() {
    setDownloadError(null);
    try {
      const fresh = await unwrap(
        api.GET("/api/v1/files/{object_id}/download-url", { params: { path: { object_id: objectId } } }),
      );
      window.location.assign(fresh.url);
    } catch (err) {
      setDownloadError(errorMessage(err));
    }
  }

  return (
    <div className={styles.result}>
      <div className={styles.stack}>
        {link.data ? (
          <video
            className={styles.preview}
            src={link.data.url}
            controls
            preload="metadata"
            aria-label={synthetic ? "Vista previa del autotest (señal sintética)" : "Vista previa del vídeo"}
          />
        ) : link.isError ? (
          <Alert tone="error">{errorMessage(link.error)}</Alert>
        ) : (
          <Spinner label="Preparando vista previa" />
        )}
      </div>
      <div className={styles.stack}>
        <Alert tone="success">
          Verificado en el servidor con ffprobe: la salida cumple la especificación solicitada.
          {synthetic ? " Es una señal sintética de prueba técnica, no contenido de DEKEN." : ""}
        </Alert>
        <KeyValues items={mediaSummary(output)} />
        <div className={styles.row}>
          <Button variant="primary" onClick={download}>
            <Download size={16} aria-hidden="true" />
            Descargar MP4
          </Button>
        </div>
        {downloadError ? <Alert tone="error">{downloadError}</Alert> : null}
      </div>
    </div>
  );
}

export function JobDetailView({ jobId, canManage }: { jobId: string; canManage: boolean }) {
  const query = useJob(jobId);
  const invalidate = useInvalidate();
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Spinner label="Cargando trabajo" />;
  if (query.isError) return <Alert tone="error">{errorMessage(query.error)}</Alert>;

  const { job, events, outputs } = query.data;
  const verifiedVideos = outputs.filter((o) => o.verified && o.kind === "video");
  const synthetic = job.type.startsWith("system.");

  async function act(action: "cancel" | "retry") {
    setBusy(true);
    setActionError(null);
    try {
      const path = action === "cancel" ? "/api/v1/jobs/{job_id}/cancel" : "/api/v1/jobs/{job_id}/retry";
      await unwrap(api.POST(path, { params: { path: { job_id: jobId } } }));
      await invalidate(keys.job(jobId), ["jobs"], keys.status);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      label={`Trabajo ${shortId(job.id)}`}
      title={jobTypeLabel(job.type)}
      actions={<JobStatusBadge status={job.status} />}
    >
      {!isTerminal(job.status) ? (
        <div className={styles.stack} aria-live="polite">
          <ProgressBar value={job.progress} label="Progreso del trabajo" />
          <span className={styles.muted}>
            {formatPercent(job.progress)} · {job.progress_message ?? (job.status === "queued" ? "Esperando a un worker" : "")}
            {job.cancel_requested ? " · cancelación solicitada" : ""}
          </span>
        </div>
      ) : null}

      {job.error ? (
        <Alert tone="error">
          <span>
            <strong>{String(job.error.code)}</strong>: {String(job.error.message)}
            {job.error.details ? (
              <pre className={styles.code}>{JSON.stringify(job.error.details, null, 2)}</pre>
            ) : null}
          </span>
        </Alert>
      ) : null}

      {verifiedVideos.map((o) => (
        <VideoOutput key={o.stored_object.id} output={o} synthetic={synthetic} />
      ))}

      <KeyValues
        items={[
          ["Intentos", `${job.attempts} de ${job.max_attempts}`],
          ["Cola", job.queue],
          ["Creado", formatDateTime(job.created_at)],
          ["Inicio", formatDateTime(job.started_at)],
          ["Fin", formatDateTime(job.finished_at)],
        ]}
      />

      {canManage ? (
        <div className={styles.row}>
          {!isTerminal(job.status) ? (
            <Button variant="danger" size="small" onClick={() => act("cancel")} busy={busy} disabled={job.cancel_requested}>
              Cancelar trabajo
            </Button>
          ) : null}
          {job.status === "failed" || job.status === "cancelled" ? (
            <Button size="small" onClick={() => act("retry")} busy={busy}>
              Reintentar
            </Button>
          ) : null}
        </div>
      ) : null}
      {actionError ? <Alert tone="error">{actionError}</Alert> : null}

      <details>
        <summary>Historial de eventos ({events.length})</summary>
        <ol className={styles.events}>
          {events.map((e) => (
            <li key={e.id}>
              <time dateTime={e.occurred_at}>{formatDateTime(e.occurred_at)}</time>
              <span>
                <span className="label">{e.kind}</span> {e.message}
              </span>
            </li>
          ))}
        </ol>
      </details>
    </Card>
  );
}
