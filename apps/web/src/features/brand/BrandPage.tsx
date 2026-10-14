"use client";

import { brand, contrastRatio, neutralsDark, neutralsLight, onGreen } from "@deken/brand";
import { AlertTriangle, Archive, Download, Upload } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, Badge, Button, Card, EmptyState, Field, FormRow, KeyValues, SelectField, Spinner } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { keys, useBrandAssets, useInvalidate, useMe, type BrandAsset } from "@/lib/queries";
import { uploadBrandFile } from "@/lib/upload";

import styles from "./brand.module.css";

type Background = "dark" | "light" | "any";

const BACKGROUND_LABEL: Record<Background, string> = {
  dark: "Fondo oscuro",
  light: "Fondo claro",
  any: "Cualquier fondo",
};

const KIND_LABEL = { logo: "Logotipo", font: "Tipografía", image: "Imagen corporativa" } as const;
const ACCEPT = { logo: ".png,.webp,image/png,image/webp", font: ".ttf,.otf", image: ".png,.webp,.jpg,.jpeg" } as const;

const ratio = (a: string, b: string) => `${contrastRatio(a, b).toFixed(2).replace(".", ",")}:1`;

function Swatch({ name, hex, note }: { name: string; hex: string; note?: string }) {
  return (
    <li className={styles.swatch}>
      <span className={styles.chipColor} style={{ background: hex }} aria-hidden="true" />
      <span className={styles.swatchText}>
        <strong>{name}</strong>
        <span className="mono">{hex}</span>
        {note ? <span className={styles.muted}>{note}</span> : null}
      </span>
    </li>
  );
}

function Palette() {
  return (
    <Card
      label="Paleta"
      title="Colores de marca"
      description="Dos colores de marca: el verde es el único acento y se usa plano. Los neutros derivan del gris Deken."
    >
      <ul className={styles.swatches}>
        <Swatch name="Verde Deken" hex={brand.green} note={`Texto encima: ${onGreen} (${ratio(brand.green, onGreen)})`} />
        <Swatch name="Gris Deken" hex={brand.gray} note="Bordes, separadores, superficies" />
        <Swatch name="Fondo oscuro" hex={neutralsDark.background} note={`Verde encima: ${ratio(brand.green, neutralsDark.background)}`} />
        <Swatch name="Fondo claro" hex={neutralsLight.background} />
      </ul>
      <Alert tone="info">
        Prohibido el texto blanco sobre verde ({ratio("#FFFFFF", brand.green)}): sobre verde, texto {onGreen}. Sin
        degradados, sin resplandores y sin cursiva.
      </Alert>
    </Card>
  );
}

function LogoCard({ asset, canManage }: { asset: BrandAsset; canManage: boolean }) {
  const invalidate = useInvalidate();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const usage = (asset.usage_background ?? asset.recommended_background ?? "any") as Background;
  const warnings = ((asset.analysis?.warnings as string[] | undefined) ?? []).filter(
    (w) => !(asset.color_mismatch === false && w.includes("no coincide")),
  );

  async function patch(body: { usage_background?: Background }) {
    setBusy(true);
    setError(null);
    try {
      await unwrap(api.PATCH("/api/v1/brand/assets/{asset_id}", { params: { path: { asset_id: asset.id } }, body }));
      await invalidate(keys.brand);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function archive() {
    if (!window.confirm(`¿Archivar «${asset.name}»? Deja de estar disponible para nuevas piezas.`)) return;
    setBusy(true);
    try {
      await unwrap(api.POST("/api/v1/brand/assets/{asset_id}/archive", { params: { path: { asset_id: asset.id } } }));
      await invalidate(keys.brand);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function download() {
    try {
      const link = await unwrap(
        api.GET("/api/v1/brand/assets/{asset_id}/download-url", { params: { path: { asset_id: asset.id } } }),
      );
      window.location.assign(link.url);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <li className={styles.logoCard}>
      <div className={styles.backgrounds}>
        {(["dark", "light"] as const).map((bg) => (
          <figure
            key={bg}
            className={`${styles.stage} ${bg === "dark" ? styles.stageDark : styles.stageLight} ${
              usage === bg ? styles.stageChosen : ""
            }`}
          >
            {asset.preview_url ? (
              // eslint-disable-next-line @next/next/no-img-element -- URL firmada del almacenamiento
              <img src={asset.preview_url} alt={`${asset.name} sobre ${BACKGROUND_LABEL[bg].toLowerCase()}`} />
            ) : null}
            <figcaption>
              {BACKGROUND_LABEL[bg]}
              {usage === bg ? " · uso indicado" : asset.recommended_background === bg ? " · recomendado" : ""}
            </figcaption>
          </figure>
        ))}
      </div>
      <div className={styles.logoBody}>
        <div className={styles.row}>
          <strong>{asset.name}</strong>
          {asset.family ? <Badge tone="muted">{asset.family}</Badge> : null}
          {asset.color_mismatch ? <Badge tone="warning">Color distinto al del nombre</Badge> : null}
        </div>
        <KeyValues
          items={[
            [
              "Tinta medida",
              <span key="m" className={styles.measured}>
                {asset.measured_color_hex ? (
                  <span className={styles.dotColor} style={{ background: asset.measured_color_hex }} aria-hidden="true" />
                ) : null}
                {asset.measured_color_name ?? "—"} <span className="mono">{asset.measured_color_hex ?? ""}</span>
              </span>,
            ],
            ["Color en el nombre", asset.declared_color ?? "—"],
            ["Tamaño", asset.width && asset.height ? `${asset.width}×${asset.height} px` : "—"],
            ["Proporción", asset.aspect_ratio ? `${asset.aspect_ratio.toLocaleString("es-ES")}:1` : "—"],
            ["Transparencia", asset.has_alpha ? "sí" : "no"],
            ["Fichero", <span key="f" className="mono">{asset.original_filename}</span>],
          ]}
        />
        {warnings.map((w) => (
          <p key={w} className={styles.warning}>
            <AlertTriangle size={14} aria-hidden="true" /> {w}
          </p>
        ))}
        <div className={styles.row}>
          {canManage ? (
            <SelectField
              label="Fondo de uso"
              value={usage}
              disabled={busy}
              onChange={(e) => void patch({ usage_background: e.target.value as Background })}
              options={(Object.keys(BACKGROUND_LABEL) as Background[]).map((value) => ({
                value,
                label: BACKGROUND_LABEL[value],
              }))}
            />
          ) : null}
          <Button size="small" onClick={download}>
            <Download size={14} aria-hidden="true" />
            Original
          </Button>
          {canManage ? (
            <Button size="small" variant="ghost" onClick={archive} busy={busy}>
              <Archive size={14} aria-hidden="true" />
              Archivar
            </Button>
          ) : null}
        </div>
        {error ? <Alert tone="error">{error}</Alert> : null}
      </div>
    </li>
  );
}

function UploadForm() {
  const invalidate = useInvalidate();
  const [inputKey, setInputKey] = useState(0);
  const [kind, setKind] = useState<keyof typeof KIND_LABEL>("logo");
  const [name, setName] = useState("");
  const [license, setLicense] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setResult(null);
    try {
      const asset = await uploadBrandFile(file, { kind, name: name.trim() || file.name, license_ref: license.trim() || null });
      await invalidate(keys.brand);
      setResult(
        asset.status === "ready"
          ? { tone: "success", text: `«${asset.name}» analizado y disponible.` }
          : { tone: "error", text: `Rechazado: ${asset.status_reason ?? "fichero no válido"}` },
      );
      setName("");
      setFile(null);
      setInputKey((k) => k + 1);
    } catch (err) {
      setResult({ tone: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      label="Importar"
      title="Añadir recurso oficial"
      description="Solo ficheros oficiales de Grupo Deken. La plataforma mide proporción, color y transparencia: no se fía del nombre del fichero."
    >
      <form className={styles.form} onSubmit={submit}>
        <FormRow>
          <SelectField
            label="Tipo"
            value={kind}
            onChange={(e) => setKind(e.target.value as keyof typeof KIND_LABEL)}
            options={Object.entries(KIND_LABEL).map(([value, label]) => ({ value, label }))}
          />
          <Field label="Nombre" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} placeholder="p. ej. DEKEN verde" />
        </FormRow>
        <Field
          label="Fichero"
          type="file"
          key={inputKey}
          accept={ACCEPT[kind]}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          hint={kind === "logo" ? "PNG o WebP con transparencia" : kind === "font" ? "TTF u OTF" : "PNG, WebP o JPEG"}
          data-testid="brand-file-input"
          required
        />
        <Field
          label="Licencia o referencia (opcional)"
          value={license}
          onChange={(e) => setLicense(e.target.value)}
          maxLength={200}
        />
        <div>
          <Button type="submit" variant="primary" busy={busy} disabled={!file}>
            <Upload size={16} aria-hidden="true" />
            Subir y analizar
          </Button>
        </div>
        {result ? <Alert tone={result.tone}>{result.text}</Alert> : null}
      </form>
    </Card>
  );
}

export function BrandPage() {
  const me = useMe();
  const assets = useBrandAssets();
  const canManage = me.data?.permissions.includes("brand:manage") ?? false;
  const list = assets.data ?? [];
  const logos = list.filter((a) => a.kind === "logo");
  const images = list.filter((a) => a.kind === "image");
  const fonts = list.filter((a) => a.kind === "font");

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className="label">Marca DEKEN</span>
        <h1>Identidad visual oficial</h1>
        <p className={styles.muted}>
          Logotipos, tipografías y reglas que usan todas las piezas. Las composiciones solo pueden usar recursos de esta
          sección.
        </p>
      </header>

      <Palette />
      {canManage ? <UploadForm /> : null}

      {assets.isPending ? (
        <Spinner label="Cargando recursos de marca" />
      ) : assets.isError ? (
        <Alert tone="error">{errorMessage(assets.error)}</Alert>
      ) : (
        <>
          <Card label="Logotipos" title={`Logotipos oficiales (${logos.length})`}>
            {logos.length ? (
              <ul className={styles.logos}>
                {logos.map((a) => (
                  <LogoCard key={a.id} asset={a} canManage={canManage} />
                ))}
              </ul>
            ) : (
              <EmptyState title="Aún no hay logotipos">
                <span>Sube los PNG oficiales del kit de marca. No se generan ni se redibujan logos.</span>
              </EmptyState>
            )}
          </Card>

          {images.length ? (
            <Card label="Imágenes" title={`Imágenes corporativas (${images.length})`}>
              <ul className={styles.logos}>
                {images.map((a) => (
                  <LogoCard key={a.id} asset={a} canManage={canManage} />
                ))}
              </ul>
            </Card>
          ) : null}

          <Card
            label="Tipografías"
            title="Tipografías"
            description="Montserrat (titulares y texto) e IBM Plex Mono (datos técnicos) ya están integradas en la plataforma y en las composiciones."
          >
            {fonts.length ? (
              <ul className={styles.fonts}>
                {fonts.map((f) => (
                  <li key={f.id}>
                    <strong>{f.name}</strong>
                    <span>
                      {f.font_family} · {f.font_style} · peso {f.font_weight}
                    </span>
                    <span className="mono">{f.original_filename}</span>
                    {f.notes ? (
                      <span className={styles.warning}>
                        <AlertTriangle size={14} aria-hidden="true" /> {f.notes}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.muted}>No se han subido ficheros de tipografía adicionales.</p>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
