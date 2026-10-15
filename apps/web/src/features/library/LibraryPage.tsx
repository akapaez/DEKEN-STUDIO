"use client";

import { Search, Volume2, VolumeX } from "lucide-react";
import type { Route } from "next";
import Link from "next/link";
import { useDeferredValue, useState } from "react";

import { Alert, Badge, Button, EmptyState, SelectField, Spinner } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { formatClock } from "@/lib/format";
import { useMe, useMediaAssets, useMediaTags, type MediaAsset, type MediaFilters } from "@/lib/queries";

import { CONSENT, MEDIA_STATUS, ORIENTATION, statusOf } from "./labels";
import styles from "./library.module.css";
import { Thumb } from "./Thumb";
import { UploadPanel } from "./UploadPanel";

const any = { value: "", label: "Todas" };

function AssetCard({ asset }: { asset: MediaAsset }) {
  const status = statusOf(asset.status);
  const consent = CONSENT[asset.consent_status];
  return (
    <li>
      <Link href={`/biblioteca/${asset.id}` as Route} className={styles.card} aria-label={`Abrir ${asset.title}`}>
        <Thumb
          posterUrl={asset.poster_url}
          stripUrl={asset.strip_url}
          stripFrames={asset.strip_frames}
          width={asset.width}
          height={asset.height}
          label={`Fotograma de ${asset.title}`}
        />
        <div className={styles.cardBody}>
          <div className={styles.cardMeta}>
            <span className="mono">{formatClock(asset.duration_s)}</span>
            {asset.orientation ? <span>{ORIENTATION[asset.orientation]}</span> : null}
            {asset.width && asset.height ? <span className="mono">{`${asset.width}×${asset.height}`}</span> : null}
            {asset.dynamic_range && asset.dynamic_range !== "sdr" ? (
              <span className="mono" title={`HDR ${asset.dynamic_range.toUpperCase()}`}>
                HDR
              </span>
            ) : null}
            {asset.has_audio === false ? (
              <VolumeX size={14} aria-label="Sin audio" />
            ) : asset.has_audio ? (
              <Volume2 size={14} aria-label="Con audio" />
            ) : null}
          </div>
          <strong className={styles.cardTitle}>{asset.title}</strong>
          <div className={styles.badges}>
            {asset.status !== "ready" ? <Badge tone={status.tone}>{status.label}</Badge> : null}
            {asset.status === "ready" && !asset.usable_for_production ? (
              <Badge tone="warning">Derechos: {consent?.label.toLowerCase() ?? "sin revisar"}</Badge>
            ) : null}
          </div>
          {asset.tags.length ? (
            <ul className={styles.tags} aria-label="Etiquetas">
              {asset.tags.slice(0, 4).map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </Link>
    </li>
  );
}

export function LibraryPage() {
  const me = useMe();
  const canUpload = me.data?.permissions.includes("media:write") ?? false;
  const [q, setQ] = useState("");
  const [tag, setTag] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [orientation, setOrientation] = useState("");
  const [audio, setAudio] = useState("");
  const [consent, setConsent] = useState("");
  const deferredQ = useDeferredValue(q.trim());

  const filters: MediaFilters = {
    ...(deferredQ ? { q: deferredQ } : {}),
    ...(tag ? { tag: [tag] } : {}),
    ...(status ? { status } : {}),
    ...(orientation ? { orientation: orientation as MediaFilters["orientation"] } : {}),
    ...(audio ? { has_audio: audio === "yes" } : {}),
    ...(consent ? { consent: consent as MediaFilters["consent"] } : {}),
  };
  const list = useMediaAssets(filters);
  const tags = useMediaTags();
  const assets = list.data?.pages.flatMap((p) => p.items) ?? [];
  const total = list.data?.pages[0]?.total ?? 0;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className="label">Biblioteca audiovisual</span>
        <h1>Grabaciones de DEKEN</h1>
        <p className={styles.lead}>
          Material real de fábrica y producto. Los originales no se modifican nunca: la galería y el reproductor usan
          derivados (póster, tira y proxy) generados en el servidor.
        </p>
      </header>

      {canUpload ? <UploadPanel /> : null}

      <section className={styles.filters} aria-label="Filtros">
        <div className={styles.search}>
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar por título, fichero, descripción o lugar"
            aria-label="Buscar en la biblioteca"
          />
        </div>
        <SelectField
          label="Estado"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          options={[any, ...Object.entries(MEDIA_STATUS).map(([value, s]) => ({ value, label: s.label }))]}
        />
        <SelectField
          label="Orientación"
          value={orientation}
          onChange={(e) => setOrientation(e.target.value)}
          options={[any, ...Object.entries(ORIENTATION).map(([value, label]) => ({ value, label }))]}
        />
        <SelectField
          label="Audio"
          value={audio}
          onChange={(e) => setAudio(e.target.value)}
          options={[any, { value: "yes", label: "Con audio" }, { value: "no", label: "Sin audio" }]}
        />
        <SelectField
          label="Consentimiento"
          value={consent}
          onChange={(e) => setConsent(e.target.value)}
          options={[any, ...Object.entries(CONSENT).map(([value, c]) => ({ value, label: c.label }))]}
        />
      </section>

      {tags.data && tags.data.length > 0 ? (
        <div className={styles.tagFilter} role="group" aria-label="Filtrar por etiqueta">
          {tags.data.slice(0, 30).map((t) => (
            <button
              key={t.tag}
              type="button"
              className={`${styles.chip} ${tag === t.tag ? styles.chipActive : ""}`}
              aria-pressed={tag === t.tag}
              onClick={() => setTag(tag === t.tag ? null : t.tag)}
            >
              {t.tag} <span className="mono">{t.count}</span>
            </button>
          ))}
        </div>
      ) : null}

      {list.isPending ? (
        <Spinner label="Cargando la biblioteca" />
      ) : list.isError ? (
        <Alert tone="error">{errorMessage(list.error)}</Alert>
      ) : assets.length === 0 ? (
        <EmptyState title={Object.keys(filters).length ? "Ningún vídeo coincide con los filtros" : "La biblioteca está vacía"}>
          {canUpload && !Object.keys(filters).length ? (
            <span>Sube las primeras grabaciones reales de DEKEN con el panel de importación.</span>
          ) : null}
        </EmptyState>
      ) : (
        <>
          <p className={styles.muted} aria-live="polite">
            {total === 1 ? "1 vídeo" : `${total} vídeos`}
          </p>
          <ul className={styles.grid} aria-label="Vídeos">
            {assets.map((a) => (
              <AssetCard key={a.id} asset={a} />
            ))}
          </ul>
          {list.hasNextPage ? (
            <div>
              <Button onClick={() => list.fetchNextPage()} busy={list.isFetchingNextPage}>
                Cargar más
              </Button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
