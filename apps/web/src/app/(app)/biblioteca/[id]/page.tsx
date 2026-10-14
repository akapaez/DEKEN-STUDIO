import type { Metadata } from "next";

import { AssetDetail } from "@/features/library/AssetDetail";

export const metadata: Metadata = { title: "Vídeo · Biblioteca" };

export default async function AssetPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AssetDetail id={id} />;
}
