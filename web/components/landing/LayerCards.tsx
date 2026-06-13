import { LAYER_META } from "@/lib/meta";

const WHAT: Record<string, string> = {
  L1: "Вход: jailbreak / вредоносный интент",
  L2: "Поведение: rate-limit + счётчик попыток",
  L3: "RBAC: фильтр RAG-чанков по роли",
  L4: "Выход: PII, секреты, canary-утечка",
};

export function LayerCards() {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-slate-500">Многослойная защита</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {(Object.keys(LAYER_META) as (keyof typeof LAYER_META)[]).map((k) => {
          const m = LAYER_META[k];
          return (
            <div key={k} className="rounded-xl border border-border bg-surface p-4">
              <div className="font-mono text-sm font-bold" style={{ color: `var(${m.cssVar})` }}>
                {k}
              </div>
              <div className="mt-1 text-sm font-medium text-slate-200">{m.label}</div>
              <div className="mt-1 text-xs text-slate-500">{WHAT[k]}</div>
              <div className="mt-2 font-mono text-[10px] text-slate-600">{m.tool}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
