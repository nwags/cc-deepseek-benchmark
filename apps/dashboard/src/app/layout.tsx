import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Phase 3 Router Benchmark Dashboard",
  description: "Claude Code backend benchmark dashboard for Phase 3 router experiments"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
