const STACK = [
  "NeMo Guardrails",
  "LangGraph",
  "MCP CVE",
  "ChromaDB",
  "Ollama",
  "Langfuse",
  "FastAPI",
  "Next.js",
];

export function StackChips() {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-slate-500">Стек</h2>
      <div className="flex flex-wrap gap-2">
        {STACK.map((s) => (
          <span key={s} className="rounded-full border border-border bg-surface px-3 py-1 text-xs text-slate-300">
            {s}
          </span>
        ))}
      </div>
    </section>
  );
}
