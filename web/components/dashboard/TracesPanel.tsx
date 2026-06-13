"use client";

import { useEffect, useState } from "react";
import { Clock, ExternalLink } from "lucide-react";
import { useLangfuseBase } from "@/lib/hooks";

type Trace = { id: string; name: string; ts: string };
type TR = { available: boolean; traces?: Trace[] };

export function TracesPanel() {
  const [tr, setTr] = useState<TR | null>(null);
  const lf = useLangfuseBase();

  useEffect(() => {
    fetch("/api/traces")
      .then((r) => r.json())
      .then((d) => setTr(d))
      .catch(() => setTr({ available: false }));
  }, []);

  const list = tr?.available ? tr.traces ?? [] : null;

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <Clock className="h-4 w-4 text-accent" /> Последние трейсы
      </h3>

      {!tr && <p className="mt-3 text-xs text-slate-500">Загрузка…</p>}
      {tr && !tr.available && (
        <p className="mt-3 text-xs text-slate-500">Langfuse недоступен или ключи не настроены.</p>
      )}
      {list && list.length === 0 && <p className="mt-3 text-xs text-slate-500">Трейсов пока нет.</p>}
      {list && list.length > 0 && (
        <ul className="mt-3 space-y-2">
          {list.map((t) => (
            <li key={t.id} className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate text-slate-400" title={t.name}>
                {t.name}
              </span>
              <a
                href={`${lf}/trace/${t.id}`}
                target="_blank"
                rel="noreferrer"
                className="flex shrink-0 items-center gap-1 text-accent hover:underline"
              >
                <ExternalLink className="h-3 w-3" /> trace
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
