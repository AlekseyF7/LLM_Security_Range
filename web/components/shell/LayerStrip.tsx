"use client";

import { useApp } from "./AppState";
import { LAYER_META } from "@/lib/meta";

export function LayerStrip() {
  const { guardrailsEnabled } = useApp();
  return (
    <div className="hidden items-center gap-1.5 lg:flex">
      {(Object.keys(LAYER_META) as (keyof typeof LAYER_META)[]).map((k) => {
        const m = LAYER_META[k];
        const active = guardrailsEnabled || k === "L3"; // L3 (RBAC) is always on
        return (
          <div
            key={k}
            title={`${k} · ${m.label} · ${m.tool}${active ? "" : " (отключён)"}`}
            className="rounded-md border px-2 py-1 font-mono text-[10px] transition"
            style={
              active
                ? { color: `var(${m.cssVar})`, borderColor: `var(${m.cssVar})`, background: "rgba(255,255,255,0.03)" }
                : { color: "#475569", borderColor: "var(--border)", background: "transparent" }
            }
          >
            <span className="font-bold">{k}</span>
          </div>
        );
      })}
    </div>
  );
}
