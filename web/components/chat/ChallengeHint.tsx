"use client";

import { Lightbulb } from "lucide-react";
import type { Challenge } from "@/lib/types";

/** How-to-pass hint for the active challenge: technique + the auto-applied
 *  environment (role / guards) + the layer that defends. Read-only; the Lab
 *  already applied role+guards via AppState.applyChallengeEnv. */
export function ChallengeHint({ challenge }: { challenge: Challenge }) {
  if (!challenge.hint) return null;
  return (
    <div className="mt-1 rounded-md border border-accent/20 bg-accent/5 px-2 py-1.5 text-[11px] text-slate-300">
      <div className="flex items-start gap-1.5">
        <Lightbulb className="mt-0.5 h-3 w-3 shrink-0 text-accent" />
        <span>{challenge.hint}</span>
      </div>
      <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-slate-500">
        <span>роль: <b className="text-slate-300">{challenge.recommendedRole}</b> ✓</span>
        <span>guards: <b className="text-slate-300">{challenge.recommendedGuards}</b> ✓</span>
        {challenge.expected_block_layer && challenge.expected_block_layer !== "none" && (
          <span>держит: <b className="text-slate-300">{challenge.expected_block_layer}</b></span>
        )}
      </div>
    </div>
  );
}
