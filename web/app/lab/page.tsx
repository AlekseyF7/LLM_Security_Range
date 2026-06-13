import { TechniqueCatalog } from "@/components/lab/TechniqueCatalog";
import { ChallengeList } from "@/components/lab/ChallengeList";
import { ProgressBadge } from "@/components/lab/ProgressBadge";

export default function LabPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Red-team Lab</h1>
          <p className="text-sm text-slate-400">
            Отрабатывай атаки на полигоне: выбери технику или challenge и пробей защиту в консоли.
          </p>
        </div>
        <ProgressBadge />
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-slate-500">
          Техники (OWASP LLM Top-10)
        </h2>
        <TechniqueCatalog />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-slate-500">Challenges</h2>
        <ChallengeList />
      </section>
    </div>
  );
}
