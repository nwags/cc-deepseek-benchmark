import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Coding Agent Benchmark Dashboard",
  description: "Claude Code backend benchmark dashboard for model and route experiments"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
