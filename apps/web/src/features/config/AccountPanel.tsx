"use client";

import { useState, type FormEvent } from "react";

import { Alert, Button, Card, Field, FormRow, KeyValues } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useMe } from "@/lib/queries";

export function AccountPanel() {
  const me = useMe();
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const d = new FormData(form);
    if (d.get("new_password") !== d.get("confirm")) {
      setError("Las contraseñas nuevas no coinciden");
      return;
    }
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await unwrap(
        api.POST("/api/v1/auth/password", {
          body: {
            current_password: String(d.get("current_password")),
            new_password: String(d.get("new_password")),
          },
        }),
      );
      setDone(true);
      form.reset();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {me.data ? (
        <Card label="Cuenta" title={me.data.user.full_name}>
          <KeyValues
            items={[
              ["Email", me.data.user.email],
              ["Rol", me.data.user.role],
              ["Permisos", me.data.permissions.join(", ")],
              ["La sesión caduca", formatDateTime(me.data.session_expires_at)],
            ]}
          />
        </Card>
      ) : null}
      <Card label="Seguridad" title="Cambiar contraseña" description="Al cambiarla se cierran tus otras sesiones abiertas.">
        <form onSubmit={submit}>
          <FormRow>
            <Field label="Contraseña actual" name="current_password" type="password" required autoComplete="current-password" />
            <Field label="Contraseña nueva" name="new_password" type="password" required minLength={12} autoComplete="new-password" hint="Mínimo 12 caracteres." />
            <Field label="Repite la nueva" name="confirm" type="password" required minLength={12} autoComplete="new-password" />
            <Button type="submit" variant="primary" busy={busy}>
              Guardar
            </Button>
          </FormRow>
        </form>
        {error ? <Alert tone="error">{error}</Alert> : null}
        {done ? <Alert tone="success">Contraseña actualizada.</Alert> : null}
      </Card>
    </>
  );
}
