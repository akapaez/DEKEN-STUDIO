"use client";

import { Copy } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, Badge, Button, Card, EmptyState, Field, FormRow, Spinner, Table } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { formatDateTime, formatRelative } from "@/lib/format";
import { keys, useInvalidate, useWorkers, type WorkerInfo } from "@/lib/queries";

import styles from "./config.module.css";

function capabilitySummary(worker: WorkerInfo): string {
  const caps = worker.capabilities as { ffmpeg_version?: string; encoders?: string[] };
  const parts = [] as string[];
  if (caps.ffmpeg_version) parts.push(`FFmpeg ${caps.ffmpeg_version}`);
  if (caps.encoders?.length) parts.push(caps.encoders.join(", "));
  return parts.join(" · ") || "Sin datos (aún no se ha conectado)";
}

export function WorkersPanel({ canManage }: { canManage: boolean }) {
  const workers = useWorkers();
  const invalidate = useInvalidate();
  const [created, setCreated] = useState<{ name: string; token: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const queues = ["render", "analysis"].filter((q) => data.get(`queue-${q}`) === "on") as Array<"render" | "analysis">;
    setBusy(true);
    setError(null);
    try {
      const result = await unwrap(
        api.POST("/api/v1/workers", { body: { name: String(data.get("name") ?? ""), queues } }),
      );
      setCreated({ name: result.worker.name, token: result.token });
      setCopied(false);
      form.reset();
      await invalidate(keys.workers, keys.status);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(worker: WorkerInfo) {
    if (!window.confirm(`¿Revocar el worker "${worker.name}"? Dejará de poder conectarse.`)) return;
    try {
      await unwrap(api.POST("/api/v1/workers/{worker_id}/revoke", { params: { path: { worker_id: worker.id } } }));
      await invalidate(keys.workers, keys.status);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const origin = typeof window === "undefined" ? "" : window.location.origin;

  return (
    <div className={styles.stack}>
      <Card
        label="Procesamiento"
        title="Workers"
        description="Equipos que ejecutan los trabajos de vídeo (p. ej. el PC con Windows/WSL2). Solo abren conexiones salientes hacia la API: no necesitan puertos abiertos."
      >
        {workers.isPending ? (
          <Spinner />
        ) : workers.isError ? (
          <Alert tone="error">{errorMessage(workers.error)}</Alert>
        ) : workers.data.length === 0 ? (
          <EmptyState title="No hay workers registrados">
            Registra el primero con el formulario de abajo y arráncalo con el token generado.
          </EmptyState>
        ) : (
          <Table caption="Workers registrados">
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Estado</th>
                <th scope="col">Colas</th>
                <th scope="col">Capacidades</th>
                <th scope="col">Última conexión</th>
                {canManage ? <th scope="col">Acciones</th> : null}
              </tr>
            </thead>
            <tbody>
              {workers.data.map((w) => (
                <tr key={w.id}>
                  <td>
                    <strong>{w.name}</strong>
                    <div className="label">dkw_{w.token_prefix}…</div>
                  </td>
                  <td>
                    {w.status === "revoked" ? (
                      <Badge tone="error">Revocado</Badge>
                    ) : w.online ? (
                      <Badge tone="ok">En línea</Badge>
                    ) : (
                      <Badge tone="muted">Desconectado</Badge>
                    )}
                  </td>
                  <td>{w.queues.join(", ")}</td>
                  <td className={styles.muted}>
                    {capabilitySummary(w)}
                    {w.hostname ? <div className="label">{w.hostname}</div> : null}
                  </td>
                  <td title={formatDateTime(w.last_seen_at)}>{formatRelative(w.last_seen_at)}</td>
                  {canManage ? (
                    <td>
                      {w.status === "active" ? (
                        <Button variant="danger" size="small" onClick={() => revoke(w)}>
                          Revocar
                        </Button>
                      ) : null}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {canManage ? (
        <Card label="Alta" title="Registrar un worker">
          <form onSubmit={register} className={styles.stack}>
            <FormRow>
              <Field label="Nombre del equipo" name="name" required minLength={3} maxLength={100} placeholder="PC-Produccion-WSL2" />
              <fieldset style={{ border: "none", padding: 0, margin: 0, display: "flex", gap: 16 }}>
                <legend className="label">Colas</legend>
                <label>
                  <input type="checkbox" name="queue-render" defaultChecked /> Render
                </label>
                <label>
                  <input type="checkbox" name="queue-analysis" defaultChecked /> Análisis
                </label>
              </fieldset>
              <Button type="submit" variant="primary" busy={busy}>
                Registrar worker
              </Button>
            </FormRow>
          </form>
          {error ? <Alert tone="error">{error}</Alert> : null}
          {created ? (
            <div className={styles.token} role="status">
              <strong>Token del worker «{created.name}». Se muestra una sola vez: cópialo ahora.</strong>
              <pre className={styles.code} data-testid="worker-token">{created.token}</pre>
              <div className={styles.row}>
                <Button
                  size="small"
                  onClick={async () => {
                    await navigator.clipboard.writeText(created.token);
                    setCopied(true);
                  }}
                >
                  <Copy size={14} aria-hidden="true" /> {copied ? "Copiado" : "Copiar token"}
                </Button>
              </div>
              <span className={styles.muted}>Arranque en el equipo (WSL2/Linux), desde el repositorio:</span>
              <pre className={styles.code}>{`export DEKEN_API_URL=${origin}
export DEKEN_WORKER_TOKEN=<token>
uv run deken-worker check
uv run deken-worker run`}</pre>
            </div>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}
