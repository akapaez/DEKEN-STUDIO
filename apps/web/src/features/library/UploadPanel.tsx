"use client";

import { Upload, X } from "lucide-react";
import type { Route } from "next";
import Link from "next/link";
import { useRef, useState, type DragEvent } from "react";

import { Alert, Badge, Button, Card, ProgressBar } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { formatBytes, formatPercent } from "@/lib/format";
import { keys, useInvalidate } from "@/lib/queries";
import { isAbort, uploadMediaFile, type UploadState } from "@/lib/upload";

import { statusOf } from "./labels";
import styles from "./library.module.css";

const ACCEPT = ".mp4,.mov,video/mp4,video/quicktime";
const ALLOWED = /\.(mp4|mov)$/i;

interface Item {
  key: string;
  file: File;
  state: UploadState;
  error?: string;
  result?: { id: string; status: string; reason?: string | null };
  controller: AbortController;
}

const PHASE: Record<UploadState["phase"], string> = {
  starting: "Preparando",
  uploading: "Subiendo",
  verifying: "Verificando en el servidor",
  done: "Subido",
  failed: "Error",
  cancelled: "Cancelado",
};

export function UploadPanel() {
  const [items, setItems] = useState<Item[]>([]);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const running = useRef(false);
  const queue = useRef<Item[]>([]);
  const invalidate = useInvalidate();

  const update = (key: string, patch: Partial<Item>) =>
    setItems((list) => list.map((it) => (it.key === key ? { ...it, ...patch } : it)));

  async function drain() {
    if (running.current) return;
    running.current = true;
    try {
      for (let item = queue.current.shift(); item; item = queue.current.shift()) {
        const { key, file, controller } = item;
        if (controller.signal.aborted) continue;
        try {
          const asset = await uploadMediaFile(file, {
            signal: controller.signal,
            onState: (state) => update(key, { state }),
          });
          update(key, { result: { id: asset.id, status: asset.status, reason: asset.status_reason } });
        } catch (err) {
          if (!isAbort(err)) update(key, { error: errorMessage(err) });
        }
        await invalidate(keys.media);
      }
    } finally {
      running.current = false;
    }
  }

  function add(files: FileList | File[]) {
    const accepted: Item[] = [];
    for (const file of Array.from(files)) {
      const item: Item = {
        key: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
        file,
        state: { phase: "starting", loaded: 0, total: file.size },
        controller: new AbortController(),
      };
      if (!ALLOWED.test(file.name)) {
        item.state = { ...item.state, phase: "failed" };
        item.error = "Solo se admiten vídeos MP4 o MOV";
      } else {
        accepted.push(item);
      }
      setItems((list) => [item, ...list]);
    }
    queue.current.push(...accepted);
    void drain();
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files.length) add(event.dataTransfer.files);
  }

  return (
    <Card
      label="Importar"
      title="Subir grabaciones"
      description="MP4 o MOV originales de DEKEN. Se suben por partes directamente al almacenamiento, se validan en el servidor y el original se guarda sin modificar."
    >
      <div
        className={`${styles.dropzone} ${dragging ? styles.dropzoneActive : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <Upload size={22} aria-hidden="true" />
        <span>Arrastra aquí los vídeos o</span>
        <Button variant="primary" onClick={() => input.current?.click()}>
          Elegir ficheros
        </Button>
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          aria-label="Ficheros de vídeo"
          data-testid="media-file-input"
          onChange={(e) => {
            if (e.target.files?.length) add(e.target.files);
            e.target.value = "";
          }}
        />
      </div>
      {items.length > 0 ? (
        <ul className={styles.uploads} aria-label="Subidas">
          {items.map((item) => {
            const { state } = item;
            const fraction = state.total ? state.loaded / state.total : 0;
            const active = ["starting", "uploading", "verifying"].includes(state.phase) && !item.error;
            const status = item.result ? statusOf(item.result.status) : null;
            return (
              <li key={item.key} className={styles.uploadItem}>
                <div className={styles.uploadHead}>
                  <strong className={styles.uploadName}>{item.file.name}</strong>
                  <span className={styles.muted}>{formatBytes(item.file.size)}</span>
                  {status ? (
                    <Badge tone={status.tone}>{status.label}</Badge>
                  ) : (
                    <Badge tone={item.error ? "error" : active ? "active" : "muted"}>{PHASE[state.phase]}</Badge>
                  )}
                  {active ? (
                    <Button size="small" variant="ghost" onClick={() => item.controller.abort()}>
                      <X size={14} aria-hidden="true" />
                      Cancelar
                    </Button>
                  ) : null}
                </div>
                {active ? (
                  <>
                    <ProgressBar value={fraction} label={`Progreso de ${item.file.name}`} />
                    <span className={styles.muted}>
                      {PHASE[state.phase]} · {formatPercent(fraction)} · {formatBytes(state.loaded)} de{" "}
                      {formatBytes(state.total)}
                    </span>
                  </>
                ) : null}
                {item.error ? <Alert tone="error">{item.error}</Alert> : null}
                {item.result?.reason ? <span className={styles.muted}>{item.result.reason}</span> : null}
                {item.result ? (
                  <Link href={`/biblioteca/${item.result.id}` as Route} className={styles.link}>
                    Ver ficha
                  </Link>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </Card>
  );
}
