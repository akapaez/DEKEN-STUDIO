import type { Metadata } from "next";

import { BrandPage } from "@/features/brand/BrandPage";

export const metadata: Metadata = { title: "Marca DEKEN" };

export default function MarcaPage() {
  return <BrandPage />;
}
