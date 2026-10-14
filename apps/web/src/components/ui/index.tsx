import type { JobStatus } from "@deken/shared";
import { JOB_STATUS_LABELS } from "@deken/shared";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { useId } from "react";

import styles from "./ui.module.css";

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ");

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export function Button({
  variant = "secondary",
  size = "normal",
  busy = false,
  className,
  children,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "normal" | "small";
  busy?: boolean;
}) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={cx(styles.button, styles[variant], size === "small" && styles.small, className)}
    >
      {busy ? <span className={styles.spinner} aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

export function Card({
  title,
  label,
  description,
  actions,
  children,
  className,
  as: Tag = "section",
}: {
  title?: ReactNode;
  label?: string;
  description?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
  as?: "section" | "article" | "div";
}) {
  const headingId = useId();
  return (
    <Tag className={cx(styles.card, className)} aria-labelledby={title ? headingId : undefined}>
      {title || actions ? (
        <div className={styles.cardHeader}>
          <div className={styles.cardTitle}>
            {label ? <span className="label">{label}</span> : null}
            {title ? <h2 id={headingId}>{title}</h2> : null}
            {description ? <p className={styles.cardDescription}>{description}</p> : null}
          </div>
          {actions}
        </div>
      ) : null}
      {children}
    </Tag>
  );
}

export type Tone = "ok" | "active" | "error" | "warning" | "muted";

export function Badge({ tone = "muted", children }: { tone?: Tone; children: ReactNode }) {
  const toneClass = {
    ok: styles.badgeOk,
    active: cx(styles.badgeOk, styles.badgeActive),
    error: styles.badgeError,
    warning: styles.badgeWarning,
    muted: styles.badgeMuted,
  }[tone];
  return (
    <span className={cx(styles.badge, toneClass)}>
      <span className={styles.dot} aria-hidden="true" />
      {children}
    </span>
  );
}

const JOB_TONES: Record<JobStatus, Tone> = {
  queued: "muted",
  processing: "active",
  completed: "ok",
  failed: "error",
  cancelled: "warning",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return <Badge tone={JOB_TONES[status]}>{JOB_STATUS_LABELS[status]}</Badge>;
}

export function Field({
  label,
  hint,
  error,
  ...input
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string | null }) {
  const id = useId();
  const hintId = `${id}-hint`;
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.fieldLabel}>
        {label}
      </label>
      <input
        id={id}
        className={styles.input}
        aria-invalid={error ? true : undefined}
        aria-describedby={hint || error ? hintId : undefined}
        {...input}
      />
      {error ? (
        <span id={hintId} className={styles.hint} role="alert">
          {error}
        </span>
      ) : hint ? (
        <span id={hintId} className={styles.hint}>
          {hint}
        </span>
      ) : null}
    </div>
  );
}

export function SelectField({
  label,
  options,
  ...select
}: SelectHTMLAttributes<HTMLSelectElement> & { label: string; options: Array<{ value: string; label: string }> }) {
  const id = useId();
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.fieldLabel}>
        {label}
      </label>
      <select id={id} className={styles.input} {...select}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function FormRow({ children }: { children: ReactNode }) {
  return <div className={styles.formRow}>{children}</div>;
}

export function Alert({
  tone = "info",
  children,
}: {
  tone?: "info" | "error" | "success";
  children: ReactNode;
}) {
  const toneClass = { info: styles.alertInfo, error: styles.alertError, success: styles.alertSuccess }[tone];
  return (
    <div className={cx(styles.alert, toneClass)} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div
      className={styles.progress}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
    >
      <div className={styles.progressFill} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Spinner({ label = "Cargando" }: { label?: string }) {
  return (
    <span role="status" style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
      <span className={styles.spinner} aria-hidden="true" />
      <span className="visually-hidden">{label}</span>
    </span>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className={styles.empty}>
      <strong>{title}</strong>
      {children}
    </div>
  );
}

export function Table({ children, caption }: { children: ReactNode; caption: string }) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <caption className="visually-hidden">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function KeyValues({ items }: { items: Array<[string, ReactNode]> }) {
  return (
    <dl className={styles.kv}>
      {items.map(([k, v]) => (
        <div key={k} style={{ display: "contents" }}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export const tableStyles = { rowButton: styles.rowButton, rowSelected: styles.rowSelected };
