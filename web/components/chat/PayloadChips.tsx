"use client";

import { QUICK_PAYLOADS } from "@/lib/meta";

const TONE: Record<string, string> = {
  ok: "border-ok/30 text-ok hover:bg-ok/10",
  bad: "border-bad/30 text-bad hover:bg-bad/10",
  warn: "border-warn/30 text-warn hover:bg-warn/10",
};

export function PayloadChips({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {QUICK_PAYLOADS.map((p) => (
        <button
          key={p.id}
          onClick={() => onPick(p.query)}
          title={p.query}
          className={`shrink-0 rounded-md border px-2.5 py-1 font-mono text-[11px] transition ${TONE[p.tone]}`}
        >
          {p.id} · {p.label}
        </button>
      ))}
    </div>
  );
}
