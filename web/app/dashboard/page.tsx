import { StatusTiles } from "@/components/dashboard/StatusTiles";
import { Scoreboard } from "@/components/dashboard/Scoreboard";
import { TracesPanel } from "@/components/dashboard/TracesPanel";
import { ResetButton } from "@/components/dashboard/ResetButton";

export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-slate-400">
          Единый пульт: статус системы, результаты security-тестов и последние трейсы.
        </p>
      </div>
      <StatusTiles />
      <div className="grid gap-4 lg:grid-cols-2">
        <Scoreboard />
        <TracesPanel />
      </div>
      <ResetButton />
    </div>
  );
}
