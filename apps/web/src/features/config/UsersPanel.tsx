"use client";

import { ROLE_LABELS, type Role } from "@deken/shared";
import { useState, type FormEvent } from "react";

import { Alert, Badge, Button, Card, Field, FormRow, SelectField, Spinner, Table } from "@/components/ui";
import { api, errorMessage, unwrap } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import { keys, useInvalidate, useRoles, useUsers, type User } from "@/lib/queries";

import styles from "./config.module.css";

const ROLE_OPTIONS = (Object.keys(ROLE_LABELS) as Role[]).map((r) => ({ value: r, label: ROLE_LABELS[r] }));

export function UsersPanel({ currentUserId }: { currentUserId: string }) {
  const users = useUsers();
  const roles = useRoles();
  const invalidate = useInvalidate();
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resetFor, setResetFor] = useState<User | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      await invalidate(keys.users);
      return true;
    } catch (err) {
      setError(errorMessage(err));
      return false;
    }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const d = new FormData(form);
    setBusy(true);
    const ok = await run(
      () =>
        unwrap(
          api.POST("/api/v1/users", {
            body: {
              email: String(d.get("email")),
              full_name: String(d.get("full_name")),
              role: String(d.get("role")) as Role,
              password: String(d.get("password")),
            },
          }),
        ),
      "Usuario creado. Comunícale la contraseña inicial por un canal seguro.",
    );
    setBusy(false);
    if (ok) form.reset();
  }

  const update = (user: User, body: { role?: Role; is_active?: boolean }) =>
    run(
      () => unwrap(api.PATCH("/api/v1/users/{user_id}", { params: { path: { user_id: user.id } }, body })),
      "Cambios guardados.",
    );

  async function resetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resetFor) return;
    const password = String(new FormData(event.currentTarget).get("password"));
    const ok = await run(
      () =>
        unwrap(
          api.POST("/api/v1/users/{user_id}/password", {
            params: { path: { user_id: resetFor.id } },
            body: { password },
          }),
        ),
      `Contraseña restablecida para ${resetFor.email}. Sus sesiones abiertas se han cerrado.`,
    );
    if (ok) setResetFor(null);
  }

  return (
    <div className={styles.stack}>
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      {error ? <Alert tone="error">{error}</Alert> : null}
      <Card label="Accesos" title="Usuarios">
        {users.isPending ? (
          <Spinner />
        ) : users.isError ? (
          <Alert tone="error">{errorMessage(users.error)}</Alert>
        ) : (
          <Table caption="Usuarios de la plataforma">
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Email</th>
                <th scope="col">Rol</th>
                <th scope="col">Estado</th>
                <th scope="col">Último acceso</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.data.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.full_name}</strong>
                    {u.id === currentUserId ? <div className="label">Tú</div> : null}
                  </td>
                  <td>{u.email}</td>
                  <td>
                    <label className="visually-hidden" htmlFor={`role-${u.id}`}>
                      Rol de {u.full_name}
                    </label>
                    <select
                      id={`role-${u.id}`}
                      value={u.role}
                      onChange={(e) => update(u, { role: e.target.value as Role })}
                    >
                      {ROLE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>{u.is_active ? <Badge tone="ok">Activo</Badge> : <Badge tone="muted">Desactivado</Badge>}</td>
                  <td>{formatRelative(u.last_login_at)}</td>
                  <td>
                    <div className={styles.row}>
                      <Button size="small" onClick={() => update(u, { is_active: !u.is_active })}>
                        {u.is_active ? "Desactivar" : "Activar"}
                      </Button>
                      <Button size="small" variant="ghost" onClick={() => setResetFor(u)}>
                        Restablecer contraseña
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {resetFor ? (
        <Card label="Seguridad" title={`Nueva contraseña para ${resetFor.full_name}`}>
          <form onSubmit={resetPassword} className={styles.inlineForm}>
            <Field label="Contraseña nueva" name="password" type="password" required minLength={12} autoComplete="new-password" hint="Mínimo 12 caracteres." />
            <Button type="submit" variant="primary">
              Guardar
            </Button>
            <Button variant="ghost" onClick={() => setResetFor(null)}>
              Cancelar
            </Button>
          </form>
        </Card>
      ) : null}

      <Card label="Alta" title="Crear usuario">
        <form onSubmit={create} className={styles.stack}>
          <FormRow>
            <Field label="Nombre completo" name="full_name" required maxLength={200} />
            <Field label="Email" name="email" type="email" required autoComplete="off" />
            <SelectField label="Rol" name="role" defaultValue="viewer" options={ROLE_OPTIONS} />
            <Field label="Contraseña inicial" name="password" type="password" required minLength={12} autoComplete="new-password" hint="Mínimo 12 caracteres." />
          </FormRow>
          <div>
            <Button type="submit" variant="primary" busy={busy}>
              Crear usuario
            </Button>
          </div>
        </form>
      </Card>

      {roles.data ? (
        <Card label="Referencia" title="Roles y permisos">
          <Table caption="Permisos por rol">
            <thead>
              <tr>
                <th scope="col">Rol</th>
                <th scope="col">Permisos</th>
              </tr>
            </thead>
            <tbody>
              {roles.data.map((r) => (
                <tr key={r.role}>
                  <td>{r.label}</td>
                  <td className="mono">{r.permissions.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      ) : null}
    </div>
  );
}
