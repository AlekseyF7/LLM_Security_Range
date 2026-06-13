"use client";

import { ShieldAlert, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { LAYER_META } from "@/lib/meta";
import type { Layer } from "@/lib/types";

export function VerdictChip({
  layer,
  blocked,
  errored,
  httpStatus,
}: {
  layer: Layer;
  blocked?: boolean;
  errored?: boolean;
  httpStatus?: number;
}) {
  if (errored) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md bg-white/5 px-2 py-1 text-[11px] text-warn ring-1 ring-warn/30">
        <AlertTriangle className="h-3 w-3" /> ошибка backend (не guard)
        {httpStatus ? <span className="font-mono opacity-70">HTTP {httpStatus}</span> : null}
      </span>
    );
  }
  if (blocked) {
    if (layer) {
      const m = LAYER_META[layer];
      return (
        <span
          className="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px]"
          style={{ color: `var(${m.cssVar})`, background: "rgba(255,255,255,0.04)", borderColor: `var(${m.cssVar})` }}
        >
          <ShieldAlert className="h-3 w-3" />
          <span className="font-mono font-bold">{layer}</span> · {m.label}
          <span className="opacity-60">({m.tool})</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md bg-bad/15 px-2 py-1 text-[11px] text-bad ring-1 ring-bad/40">
        <XCircle className="h-3 w-3" /> заблокировано
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-ok/15 px-2 py-1 text-[11px] text-ok ring-1 ring-ok/30">
      <CheckCircle2 className="h-3 w-3" /> прошло
    </span>
  );
}
