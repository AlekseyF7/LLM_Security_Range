"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Scenario } from "@/lib/types";

export function ScenarioCards() {
  const [items, setItems] = useState<Scenario[]>([]);

  useEffect(() => {
    fetch("/api/scenarios")
      .then((r) => r.json())
      .then((d: { scenarios: Scenario[] }) => setItems((d.scenarios ?? []).slice(0, 6)))
      .catch(() => setItems([]));
  }, []);

  if (items.length === 0) return null;

  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-slate-500">Сценарии</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((s) => (
          <Link
            key={s.id}
            href={`/console?challenge=${s.id}`}
            className="rounded-xl border border-border bg-surface p-4 transition hover:border-accent/40"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] text-accent">{s.id}</span>
              <span className="text-[10px] text-slate-500">{s.severity}</span>
            </div>
            <div className="mt-1 text-sm text-slate-200">{s.name}</div>
            <div className="mt-1 text-[10px] text-slate-500">{s.owasp}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
