import type { Metadata } from "next";
import { Suspense } from "react";

import { Spinner } from "@/components/ui";
import { ConfigPage } from "@/features/config/ConfigPage";

export const metadata: Metadata = { title: "Configuración" };

export default function ConfiguracionPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <ConfigPage />
    </Suspense>
  );
}
