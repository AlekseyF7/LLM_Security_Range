"use client";

import { useState } from "react";
import { RotateCcw } from "lucide-react";
import { useApp } from "@/components/shell/AppState";
import { resolveApiUrl } from "@/lib/api";

export function ResetButton() {
  const { role } = useApp();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const isAdmin = role === "admin";

  const onReset = async () => {
    if (!isAdmin || busy) return;
    if (!window.confirm("Сбросить полигон? Будут удалены загруженные документы и L2-блоки. Seed-данные останутся.")) return;
    setBusy(true);
    setMsg(null);
    try {
      const resp = await fetch(`${resolveApiUrl()}/api/v1/system/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Role": role },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const d = (await resp.json()) as { chunks_removed: number; blocks_cleared: number };
      setMsg(`Сброшено: ${d.chunks_removed} чанков, ${d.blocks_cleared} L2-блоков.`);
    } catch (e) {
      setMsg(`Ошибка reset: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <RotateCcw className="h-4 w-4 text-accent" /> Reset range
      </h3>
      <p className="mt-1 text-xs text-slate-500">
        Удаляет загруженные через агента документы и сбрасывает L2-блоки. Seed-данные не трогает.
      </p>
      <button
        onClick={() => void onReset()}
        disabled={!isAdmin || busy}
        title={isAdmin ? "Сбросить полигон (admin)" : "Доступно только админу"}
        className={`mt-3 inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs transition ${
          isAdmin
            ? "border-bad/40 text-bad hover:bg-bad/10"
            : "cursor-not-allowed border-border text-slate-600 opacity-50"
        }`}
      >
        <RotateCcw className="h-3 w-3" /> {busy ? "Сброс…" : "Reset range"}
      </button>
      {msg && <p className="mt-2 text-xs text-slate-400">{msg}</p>}
    </div>
  );
}
