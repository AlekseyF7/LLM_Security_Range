"use client";

import { useEffect, useState } from "react";
import { Swords } from "lucide-react";

type Cat = { code: string; passed: number; total: number };
type SB = { available: boolean; ranAt?: string | null; total?: number; passed?: number; byCategory?: Cat[] };

export function Scoreboard() {
  const [sb, setSb] = useState<SB | null>(null);

  useEffect(() => {
    fetch("/api/scoreboard")
      .then((r) => r.json())
      .then((d) => setSb(d))
      .catch(() => setSb({ available: false }));
  }, []);

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold">
          <Swords className="h-4 w-4 text-accent" /> Security tests (OWASP)
        </h3>
        {sb?.available && (
          <span className="text-xs text-ok">
            {sb.passed}/{sb.total} ✓
          </span>
        )}
      </div>

      {!sb && <p className="mt-3 text-xs text-slate-500">Загрузка…</p>}

      {sb && !sb.available && (
        <p className="mt-3 text-xs text-slate-500">
          Прогона ещё не было. Запусти{" "}
          <code className="text-slate-300">npx promptfoo eval --output promptfoo-results.json</code>
        </p>
      )}

      {sb?.available && (
        <div className="mt-3 space-y-2">
          {(sb.byCategory ?? []).map((c) => {
            const pct = c.total ? Math.round((c.passed / c.total) * 100) : 0;
            return (
              <div key={c.code} className="flex items-center gap-2">
                <span className="w-28 shrink-0 truncate font-mono text-[11px] text-slate-400" title={c.code}>
                  {c.code}
                </span>
                <div className="h-1.5 flex-1 rounded-full bg-white/10">
                  <div
                    className="h-1.5 rounded-full"
                    style={{ width: `${pct}%`, background: pct === 100 ? "var(--ok)" : "var(--warn)" }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right font-mono text-[11px] text-slate-500">
                  {c.passed}/{c.total}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
