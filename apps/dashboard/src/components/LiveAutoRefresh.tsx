"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function LiveAutoRefresh({ enabled, seconds = 8 }: { enabled: boolean; seconds?: number }) {
  const router = useRouter();

  useEffect(() => {
    if (!enabled) return;
    const timer = window.setInterval(() => router.refresh(), Math.max(seconds, 3) * 1000);
    return () => window.clearInterval(timer);
  }, [enabled, router, seconds]);

  return null;
}
