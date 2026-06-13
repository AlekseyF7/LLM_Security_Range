"use client";

import { ShieldCheck, ShieldOff, Server, Cpu, Database, Clock } from "lucide-react";
import { useApp } from "@/components/shell/AppState";
import { formatUptime } from "@/lib/api";

export function StatusTiles() {
  const { status, guardrailsEnabled } = useApp();

  const tiles: { label: string; value: string; icon: typeof Server; color?: string }[] = [
    {
      label: "guardrails",
      value: guardrailsEnabled ? "ON" : "OFF",
      icon: guardrailsEnabled ? ShieldCheck : ShieldOff,
      color: guardrailsEnabled ? "var(--ok)" : "var(--warn)",
    },
    { label: "runtime", value: status?.guardrails_runtime ?? "—", icon: Server },
    { label: "chat model", value: status?.chat_model ?? "—", icon: Cpu },
    { label: "embeddings", value: status?.embedding_model ?? "—", icon: Database },
    { label: "uptime", value: formatUptime(status?.uptime_seconds), icon: Clock },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {tiles.map((t) => {
        const Icon = t.icon;
        return (
          <div key={t.label} className="rounded-xl border border-border bg-surface p-4">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-slate-500">
              <Icon className="h-3.5 w-3.5 text-accent" /> {t.label}
            </div>
            <div
              className="mt-2 truncate font-mono text-sm font-semibold"
              style={t.color ? { color: t.color } : undefined}
              title={t.value}
            >
              {t.value}
            </div>
          </div>
        );
      })}
    </div>
  );
}
