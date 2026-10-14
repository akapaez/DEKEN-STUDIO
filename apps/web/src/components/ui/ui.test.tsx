import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button, Field, JobStatusBadge, ProgressBar } from "./index";

describe("componentes de interfaz", () => {
  it("el botón ocupado se deshabilita y lo anuncia", () => {
    render(<Button busy>Guardar</Button>);
    const button = screen.getByRole("button", { name: "Guardar" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("los campos tienen etiqueta y error accesible", () => {
    render(<Field label="Email" error="Email no válido" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Email no válido");
  });

  it("la barra de progreso expone su valor", () => {
    render(<ProgressBar value={0.42} label="Progreso" />);
    expect(screen.getByRole("progressbar", { name: "Progreso" })).toHaveAttribute("aria-valuenow", "42");
  });

  it("los estados de trabajo se muestran en español", () => {
    render(<JobStatusBadge status="failed" />);
    expect(screen.getByText("Fallido")).toBeInTheDocument();
  });
});
