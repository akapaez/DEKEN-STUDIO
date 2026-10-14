"use client";

import { ArrowLeft, Archive, Download } from "lucide-react";
import type { Route } from "next";
import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  Field,
  FormRow,
  KeyValues,
  ProgressBar,
  SelectField,
  Spinner,
  TextareaField,
} from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { formatBytes, formatClock, formatDateTime, formatFps, formatPercent } from "@/lib/format";
import {
  keys,
  useInvalidate,
  useJob,
  useMe,
  useMediaAsset,
  useWaveform,
  type MediaAssetDetail,
} from "@/lib/queries";

import { CONSENT, ORIENTATION, PEOPLE, statusOf } from "./labels";
import styles from "./library.module.css";
import { Waveform } from "./Waveform";

function IngestProgress({ jobId }: { jobId: string }) {
  const job = useJob(jobId);
  const data = job.data?.job;
  if (!data) return <Spinner label="Cargando la ingesta" />;
  return (
    <div className={styles.stack} aria-live="polite">
      <ProgressBar value={data.progress} label="Progreso de la ingesta" />
      <span className={styles.muted}>
        {formatPercent(data.progress)} ·{" "}
        {data.progress_message ?? (data.status === "queued" ? "En cola: esperando a un worker de análisis" : "")}
      </span>
    </div>
  );
}

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function CatalogForm({ asset, canEdit }: { asset: MediaAssetDetail; canEdit: boolean }) {
  const invalidate = useInvalidate();
  const [title, setTitle] = useState(asset.title);
  const [description, setDescription] = useState(asset.description ?? "");
  const [tags, setTags] = useState(asset.tags.join(", "));
  const [location, setLocation] = useState(asset.location ?? "");
  const [recordedAt, setRecordedAt] = useState(toLocalInput(asset.recorded_at));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await unwrap(
        api.PATCH("/api/v1/media/assets/{asset_id}", {
          params: { path: { asset_id: asset.id } },
          body: {
            title: title.trim(),
            description: description.trim(),
            tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
            location: location.trim(),
            ...(recordedAt ? { recorded_at: new Date(recordedAt).toISOString() } : {}),
          },
        }),
      );
      await invalidate(keys.media);
      setMessage({ tone: "success", text: "Catalogación guardada" });
    } catch (err) {
      setMessage({ tone: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  if (!canEdit) {
    return (
      <Card label="Catálogo" title="Descripción y etiquetas">
        <KeyValues
          items={[
            ["Descripción", asset.description || "—"],
            ["Etiquetas", asset.tags.join(", ") || "—"],
            ["Lugar", asset.location || "—"],
            ["Grabado", formatDateTime(asset.recorded_at)],
          ]}
        />
      </Card>
    );
  }
  return (
    <Card label="Catálogo" title="Descripción y etiquetas">
      <form className={styles.stack} onSubmit={save}>
        <Field label="Título" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} />
        <TextareaField
          label="Descripción"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={4000}
          hint="Qué se ve realmente en el plano (proceso, máquina, producto). No describas lo que no aparece."
        />
        <Field
          label="Etiquetas"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          hint="Separadas por comas, p. ej.: corte, perfiles, línea 2"
        />
        <FormRow>
          <Field label="Lugar" value={location} onChange={(e) => setLocation(e.target.value)} maxLength={200} />
          <Field
            label="Fecha de grabación"
            type="datetime-local"
            value={recordedAt}
            onChange={(e) => setRecordedAt(e.target.value)}
          />
        </FormRow>
        <div className={styles.row}>
          <Button type="submit" variant="primary" busy={busy}>
            Guardar catalogación
          </Button>
        </div>
        {message ? <Alert tone={message.tone}>{message.text}</Alert> : null}
      </form>
    </Card>
  );
}

function RightsForm({ asset, canEdit }: { asset: MediaAssetDetail; canEdit: boolean }) {
  const invalidate = useInvalidate();
  const [people, setPeople] = useState(asset.people_present);
  const [consent, setConsent] = useState(asset.consent_status);
  const [reference, setReference] = useState(asset.consent_reference ?? "");
  const [restrictions, setRestrictions] = useState(asset.usage_restrictions ?? "");
  const [owner, setOwner] = useState(asset.rights_owner);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const consentInfo = CONSENT[asset.consent_status];

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await unwrap(
        api.PUT("/api/v1/media/assets/{asset_id}/rights", {
          params: { path: { asset_id: asset.id } },
          body: {
            people_present: people,
            consent_status: consent,
            consent_reference: reference.trim() || null,
            usage_restrictions: restrictions.trim() || null,
            rights_owner: owner.trim(),
          },
        }),
      );
      await invalidate(keys.media);
      setMessage({ tone: "success", text: "Derechos actualizados y registrados en la auditoría" });
    } catch (err) {
      setMessage({ tone: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  const summary = (
    <div className={styles.row}>
      {asset.usable_for_production ? (
        <Badge tone="ok">Utilizable en piezas</Badge>
      ) : (
        <Badge tone="warning">No utilizable en piezas comerciales</Badge>
      )}
      <Badge tone={consentInfo?.tone ?? "muted"}>Consentimiento: {consentInfo?.label ?? asset.consent_status}</Badge>
    </div>
  );

  if (!canEdit) {
    return (
      <Card label="Derechos de imagen" title="Personas y consentimiento">
        {summary}
        <KeyValues
          items={[
            ["Personas", PEOPLE[asset.people_present] ?? asset.people_present],
            ["Referencia", asset.consent_reference || "—"],
            ["Restricciones", asset.usage_restrictions || "—"],
            ["Titular", asset.rights_owner],
            ["Actualizado", formatDateTime(asset.rights_updated_at)],
          ]}
        />
        <p className={styles.muted}>Solo revisión o administración pueden modificar los derechos de imagen.</p>
      </Card>
    );
  }
  return (
    <Card
      label="Derechos de imagen"
      title="Personas y consentimiento"
      description="Si aparecen personas, el vídeo solo se puede usar en piezas con el consentimiento concedido y su referencia documental."
    >
      {summary}
      <form className={styles.stack} onSubmit={save}>
        <FormRow>
          <SelectField
            label="¿Aparecen personas?"
            value={people}
            onChange={(e) => setPeople(e.target.value as typeof people)}
            options={Object.entries(PEOPLE).map(([value, label]) => ({ value, label }))}
          />
          <SelectField
            label="Consentimiento"
            value={consent}
            onChange={(e) => setConsent(e.target.value as typeof consent)}
            options={Object.entries(CONSENT).map(([value, c]) => ({ value, label: c.label }))}
          />
        </FormRow>
        <Field
          label="Referencia del consentimiento"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          maxLength={300}
          hint="Obligatoria si se concede: nº de documento, expediente o registro interno."
        />
        <TextareaField
          label="Restricciones de uso"
          value={restrictions}
          onChange={(e) => setRestrictions(e.target.value)}
          maxLength={4000}
        />
        <Field label="Titular de los derechos" value={owner} onChange={(e) => setOwner(e.target.value)} required />
        <div className={styles.row}>
          <Button type="submit" variant="primary" busy={busy}>
            Guardar derechos
          </Button>
        </div>
        {message ? <Alert tone={message.tone}>{message.text}</Alert> : null}
      </form>
    </Card>
  );
}

function containerLabel(asset: MediaAssetDetail): string {
  const ext = asset.original_filename.split(".").pop()?.toLowerCase();
  if (ext === "mov") return "MOV (QuickTime)";
  if (ext === "mp4") return "MP4";
  return asset.container ?? "—";
}

function TechnicalCard({ asset }: { asset: MediaAssetDetail }) {
  const original = asset.original_object;
  return (
    <Card label="Original" title="Datos técnicos">
      <KeyValues
        items={[
          ["Fichero", <span key="f" className="mono">{asset.original_filename}</span>],
          ["Tamaño", formatBytes(original?.size_bytes ?? asset.declared_size_bytes)],
          ["Contenedor", containerLabel(asset)],
          ["Duración", formatClock(asset.duration_s)],
          [
            "Resolución",
            asset.width && asset.height
              ? `${asset.width}×${asset.height}${asset.orientation ? ` · ${ORIENTATION[asset.orientation]}` : ""}`
              : "—",
          ],
          ["Rotación (móvil)", asset.rotation ? `${asset.rotation}°` : "ninguna"],
          ["Cadencia", formatFps(asset.fps)],
          ["Vídeo", asset.video_codec ?? "—"],
          ["Audio", asset.has_audio ? (asset.audio_codec ?? "sí") : "sin audio"],
          [
            "SHA-256",
            asset.sha256 ? (
              <span key="s" className="mono" title={asset.sha256}>
                {asset.sha256.slice(0, 16)}…
              </span>
            ) : (
              "pendiente"
            ),
          ],
          ["Subido", formatDateTime(asset.created_at)],
        ]}
      />
    </Card>
  );
}

export function AssetDetail({ id }: { id: string }) {
  const query = useMediaAsset(id);
  const me = useMe();
  const invalidate = useInvalidate();
  const video = useRef<HTMLVideoElement>(null);
  const asset = query.data;
  const waveform = useWaveform(id, Boolean(asset?.has_waveform));
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"download" | "archive" | null>(null);
  const permissions = new Set(me.data?.permissions ?? []);

  if (query.isPending) return <Spinner label="Cargando el vídeo" />;
  if (query.isError || !asset) return <Alert tone="error">{errorMessage(query.error)}</Alert>;

  const status = statusOf(asset.status);

  async function downloadOriginal() {
    setBusy("download");
    setActionError(null);
    try {
      const link = await unwrap(
        api.GET("/api/v1/media/assets/{asset_id}/original-url", { params: { path: { asset_id: id } } }),
      );
      window.location.assign(link.url);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function archive() {
    if (!window.confirm("¿Archivar este vídeo? Deja de aparecer en la biblioteca; el original se conserva.")) return;
    setBusy("archive");
    setActionError(null);
    try {
      await unwrap(api.POST("/api/v1/media/assets/{asset_id}/archive", { params: { path: { asset_id: id } } }));
      await invalidate(keys.media);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={styles.page}>
      <Link href={"/biblioteca" as Route} className={styles.back}>
        <ArrowLeft size={16} aria-hidden="true" />
        Biblioteca
      </Link>
      <header className={styles.detailHeader}>
        <div className={styles.stack}>
          <span className="label">Vídeo</span>
          <h1>{asset.title}</h1>
        </div>
        <div className={styles.row}>
          <Badge tone={status.tone}>{status.label}</Badge>
          {asset.archived_at ? <Badge tone="muted">Archivado</Badge> : null}
        </div>
      </header>

      {asset.status === "processing" && asset.ingest_job_id ? (
        <Card label="Ingesta" title="Generando póster, tira, proxy y forma de onda">
          <IngestProgress jobId={asset.ingest_job_id} />
        </Card>
      ) : null}
      {["rejected", "failed", "duplicate"].includes(asset.status) ? (
        <Alert tone={asset.status === "duplicate" ? "info" : "error"}>
          {asset.status_reason ?? status.label}
          {asset.duplicate_of_id ? (
            <>
              {" "}
              <Link href={`/biblioteca/${asset.duplicate_of_id}` as Route} className={styles.link}>
                Abrir el original
              </Link>
            </>
          ) : null}
        </Alert>
      ) : null}

      <div className={styles.detailGrid}>
        <div className={styles.stack}>
          <Card label="Previsualización" title="Proxy de visionado">
            {asset.proxy_url ? (
              <video
                ref={video}
                className={styles.player}
                src={asset.proxy_url}
                poster={asset.poster_url ?? undefined}
                controls
                preload="metadata"
                aria-label={`Proxy de ${asset.title}`}
              />
            ) : (
              <p className={styles.muted}>El proxy estará disponible cuando termine la ingesta.</p>
            )}
            {asset.has_waveform && waveform.data ? (
              <Waveform
                peaks={waveform.data.peaks}
                duration={waveform.data.duration_s}
                video={video}
                onSeek={(seconds) => {
                  if (video.current) video.current.currentTime = seconds;
                }}
              />
            ) : asset.has_audio === false ? (
              <p className={styles.muted}>Este vídeo no tiene pista de audio.</p>
            ) : null}
            <p className={styles.muted}>
              El proxy es una copia ligera para revisar el material. Para montar se usa siempre el original.
            </p>
            <div className={styles.row}>
              <Button onClick={downloadOriginal} busy={busy === "download"} disabled={!asset.original_object}>
                <Download size={16} aria-hidden="true" />
                Descargar original
              </Button>
              {permissions.has("media:write") && !asset.archived_at ? (
                <Button variant="ghost" onClick={archive} busy={busy === "archive"}>
                  <Archive size={16} aria-hidden="true" />
                  Archivar
                </Button>
              ) : null}
            </div>
            {actionError ? <Alert tone="error">{actionError}</Alert> : null}
          </Card>
          <TechnicalCard asset={asset} />
        </div>
        <div className={styles.stack}>
          <CatalogForm key={`c-${asset.id}`} asset={asset} canEdit={permissions.has("media:write")} />
          <RightsForm key={`r-${asset.id}`} asset={asset} canEdit={permissions.has("media:rights")} />
        </div>
      </div>
    </div>
  );
}
