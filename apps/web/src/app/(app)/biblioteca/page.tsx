import type { Metadata } from "next";

import { LibraryPage } from "@/features/library/LibraryPage";

export const metadata: Metadata = { title: "Biblioteca" };

export default function BibliotecaPage() {
  return <LibraryPage />;
}
