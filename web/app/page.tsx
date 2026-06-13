import Link from "next/link";
import { Hero } from "@/components/landing/Hero";
import { LayerCards } from "@/components/landing/LayerCards";
import { ScenarioCards } from "@/components/landing/ScenarioCards";
import { StackChips } from "@/components/landing/StackChips";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <Hero />
      <LayerCards />
      <ScenarioCards />
      <StackChips />
      <footer className="border-t border-border pt-4 text-center text-xs text-slate-600">
        Все «секреты» в RAG — намеренно фейковые тест-фикстуры. ·{" "}
        <Link href="/console" className="text-accent hover:underline">
          Консоль
        </Link>
      </footer>
    </div>
  );
}
