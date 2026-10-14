"use client";

import { useState } from "react";

import { Alert, Badge, Card, SelectField, Spinner, Table } from "@/components/ui";
import { errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useAudit } from "@/lib/queries";

type Outcome = "success" | "failure" | "denied";

const OUTCOME_LABEL: Record<string, string> = { success: "Correcto", failure: "Fallido", denied: "Denegado" };

export function AuditPanel() {
  const [outcome, setOutcome] = useState<Outcome | "">("");
  const audit = useAudit(outcome || undefined);

  return (
    <Card
      label="Seguridad"
      title="Auditoría"
      description="Registro inmutable de accesos y acciones administrativas (últimos 100 eventos)."
      actions={
        <SelectField
          label="Resultado"
          value={outcome}
          onChange={(e) => setOutcome(e.target.value as Outcome | "")}
          options={[
            { value: "", label: "Todos" },
            { value: "success", label: "Correctos" },
            { value: "failure", label: "Fallidos" },
            { value: "denied", label: "Denegados" },
          ]}
        />
      }
    >
      {audit.isPending ? (
        <Spinner />
      ) : audit.isError ? (
        <Alert tone="error">{errorMessage(audit.error)}</Alert>
      ) : (
        <Table caption="Eventos de auditoría">
          <thead>
            <tr>
              <th scope="col">Fecha</th>
              <th scope="col">Acción</th>
              <th scope="col">Resultado</th>
              <th scope="col">Actor</th>
              <th scope="col">Objetivo</th>
              <th scope="col">IP</th>
            </tr>
          </thead>
          <tbody>
            {audit.data.items.map((e) => (
              <tr key={e.id}>
                <td>{formatDateTime(e.occurred_at)}</td>
                <td className="mono">{e.action}</td>
                <td>
                  <Badge tone={e.outcome === "success" ? "ok" : e.outcome === "denied" ? "warning" : "error"}>
                    {OUTCOME_LABEL[e.outcome] ?? e.outcome}
                  </Badge>
                </td>
                <td>{e.actor_label ?? e.actor_type}</td>
                <td className="mono">{e.target_type ? `${e.target_type}:${e.target_id?.slice(0, 8)}` : "—"}</td>
                <td className="mono">{e.ip ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Card>
  );
}
