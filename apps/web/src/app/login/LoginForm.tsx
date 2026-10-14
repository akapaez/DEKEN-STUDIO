"use client";

import type { Route } from "next";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Alert, Button, Field } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";

import styles from "./login.module.css";

/** Solo se aceptan rutas internas como destino tras el login (evita redirecciones abiertas). */
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return "/";
  return next;
}

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await unwrap(
        api.POST("/api/v1/auth/login", {
          body: { email: String(form.get("email") ?? ""), password: String(form.get("password") ?? "") },
        }),
      );
      router.replace(safeNext(params.get("next")) as Route);
      router.refresh();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      {error ? <Alert tone="error">{error}</Alert> : null}
      <Field label="Email" name="email" type="email" autoComplete="username" required autoFocus />
      <Field label="Contraseña" name="password" type="password" autoComplete="current-password" required />
      <Button type="submit" variant="primary" busy={busy}>
        Entrar
      </Button>
    </form>
  );
}
