import Link from "next/link";
import { ShieldCheck, ArrowRight } from "lucide-react";

export function Hero() {
  return (
    <section
      className="relative overflow-hidden rounded-2xl border border-accent/20 px-6 py-16 text-center"
      style={{ background: "radial-gradient(circle at 50% 0%, rgba(34,211,238,0.12), transparent 60%)" }}
    >
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-5">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-slate-400">
          <ShieldCheck className="h-3.5 w-3.5 text-accent" /> LLM security cyber range
        </span>
        <h1 className="text-4xl font-bold leading-tight sm:text-5xl">Smart Wiki</h1>
        <p className="text-lg text-slate-300">
          Киберполигон для испытаний безопасности систем на основе больших языковых моделей
        </p>
        <p className="max-w-2xl text-sm text-slate-500">
          Изолированный доверенный полигон: защищённый ИИ-ассистент по базе знаний, многослойная защита, инструментарий
          red-team и сквозная наблюдаемость. Для учебных и производственных задач.
        </p>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/console"
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-slate-900 transition hover:opacity-90"
          >
            Открыть консоль <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/lab"
            className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm transition hover:bg-white/5"
          >
            В Lab
          </Link>
        </div>
      </div>
    </section>
  );
}
