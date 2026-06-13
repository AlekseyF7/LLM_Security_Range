"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Play, CheckCircle2 } from "lucide-react";
import { getWon, PROGRESS_EVENT } from "@/lib/progress";
import type { Challenge } from "@/lib/types";

const SEV: Record<string, string> = {
  critical: "text-bad",
  high: "text-warn",
  medium: "text-slate-400",
  low: "text-slate-500",
};

export function ChallengeCard({ challenge }: { challenge: Challenge }) {
  const [won, setWon] = useState(false);

  useEffect(() => {
    const update = () => setWon(getWon().includes(challenge.id));
    update();
    window.addEventListener(PROGRESS_EVENT, update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener(PROGRESS_EVENT, update);
      window.removeEventListener("storage", update);
    };
  }, [challenge.id]);

  return (
    <div className={`rounded-xl border bg-surface p-4 transition ${won ? "border-ok/40" : "border-border"}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-accent">{challenge.id}</span>
        {won && <CheckCircle2 className="h-4 w-4 text-ok" />}
      </div>
      <h3 className="mt-1 text-sm font-medium text-slate-200">{challenge.name}</h3>
      <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
        <span>{challenge.owasp}</span>
        <span className={SEV[challenge.severity] ?? "text-slate-500"}>● {challenge.severity}</span>
      </div>
      <Link
        href={`/console?challenge=${challenge.id}`}
        className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-accent/40 px-2.5 py-1 text-xs text-accent transition hover:bg-accent/10"
      >
        <Play className="h-3 w-3" /> Старт
      </Link>
    </div>
  );
}
