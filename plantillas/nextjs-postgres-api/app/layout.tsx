import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TEMPLATE_TITLE",
  description: "Aplicación conectada a Postgres API",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="antialiased">{children}</body>
    </html>
  );
}
