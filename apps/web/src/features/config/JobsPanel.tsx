"use client";

import { JOB_STATUS_LABELS, type JobStatus } from "@deken/shared";
import { useState } from "react";

import { Alert, Card, EmptyState, JobStatusBadge, ProgressBar, SelectField, Spinner, Table, tableStyles } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { formatDateTime, formatPercent, jobTypeLabel, shortId } from "@/lib/format";
import { useJobs } from "@/lib/queries";

import styles from "./config.module.css";
import { JobDetailView } from "./JobDetailView";

const STATUSES = Object.keys(JOB_STATUS_LABELS) as JobStatus[];

export function JobsPanel({ canManage, initialJob }: { canManage: boolean; initialJob: string | null }) {
  const [status, setStatus] = useState<JobStatus | "">("");
  const [selected, setSelected] = useState<string | null>(initialJob);
  const jobs = useJobs(status || undefined, 100);

  return (
    <div className={styles.stack}>
      <Card
        label="Procesamiento"
        title="Trabajos"
        description="Cola de trabajos de render y análisis. Un trabajo solo figura como completado cuando su salida ha sido verificada en el servidor."
        actions={
          <SelectField
            label="Estado"
            value={status}
            onChange={(e) => setStatus(e.target.value as JobStatus | "")}
            options={[{ value: "", label: "Todos" }, ...STATUSES.map((s) => ({ value: s, label: JOB_STATUS_LABELS[s] }))]}
          />
        }
      >
        {jobs.isPending ? (
          <Spinner />
        ) : jobs.isError ? (
          <Alert tone="error">{errorMessage(jobs.error)}</Alert>
        ) : jobs.data.items.length === 0 ? (
          <EmptyState title="No hay trabajos con este filtro" />
        ) : (
          <Table caption="Lista de trabajos">
            <thead>
              <tr>
                <th scope="col">ID</th>
                <th scope="col">Tipo</th>
                <th scope="col">Estado</th>
                <th scope="col">Progreso</th>
                <th scope="col">Intentos</th>
                <th scope="col">Creado</th>
              </tr>
            </thead>
            <tbody>
              {jobs.data.items.map((job) => (
                <tr
                  key={job.id}
                  className={`${tableStyles.rowButton} ${selected === job.id ? tableStyles.rowSelected : ""}`}
                  onClick={() => setSelected(job.id)}
                >
                  <td className="mono">
                    <button
                      type="button"
                      onClick={() => setSelected(job.id)}
                      aria-pressed={selected === job.id}
                      style={{ background: "none", border: "none", padding: 0, cursor: "pointer", textDecoration: "underline" }}
                    >
                      {shortId(job.id)}
                    </button>
                  </td>
                  <td>{jobTypeLabel(job.type)}</td>
                  <td>
                    <JobStatusBadge status={job.status} />
                  </td>
                  <td style={{ minWidth: 140 }}>
                    <ProgressBar value={job.progress} label={`Progreso ${shortId(job.id)}`} />
                    <span className="label">{formatPercent(job.progress)}</span>
                  </td>
                  <td>
                    {job.attempts}/{job.max_attempts}
                  </td>
                  <td>{formatDateTime(job.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
      {selected ? <JobDetailView key={selected} jobId={selected} canManage={canManage} /> : null}
    </div>
  );
}
