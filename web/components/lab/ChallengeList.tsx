"use client";

import { useEffect, useState } from "react";
import { ChallengeCard } from "./ChallengeCard";
import type { Challenge, Scenario } from "@/lib/types";

export function ChallengeList() {
  const [items, setItems] = useState<Challenge[] | null>(null);

  useEffect(() => {
    fetch("/api/scenarios")
      .then((r) => r.json())
      .then((d: { scenarios: Scenario[] }) => {
        setItems((d.scenarios ?? []).map((s) => ({ ...s, mode: "bypass" as const })));
      })
      .catch(() => setItems([]));
  }, []);

  if (!items) return <p className="text-sm text-slate-500">Загрузка сценариев…</p>;
  if (items.length === 0)
    return <p className="text-sm text-slate-500">Сценарии недоступны (scenarios.yaml не найден).</p>;

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((c) => (
        <ChallengeCard key={c.id} challenge={c} />
      ))}
    </div>
  );
}
