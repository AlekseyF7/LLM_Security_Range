"use client";

import { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { getWon, PROGRESS_EVENT } from "@/lib/progress";

export function ProgressBadge() {
  const [n, setN] = useState(0);

  useEffect(() => {
    const update = () => setN(getWon().length);
    update();
    window.addEventListener(PROGRESS_EVENT, update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener(PROGRESS_EVENT, update);
      window.removeEventListener("storage", update);
    };
  }, []);

  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm">
      <Trophy className="h-4 w-4 text-accent" /> Решено: <span className="font-mono font-semibold text-ok">{n}</span>
    </span>
  );
}
