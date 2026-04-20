import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MasterAI Academy",
  description: "Plataforma interna de IA e dados",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
