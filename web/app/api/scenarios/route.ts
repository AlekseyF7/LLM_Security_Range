import { promises as fs } from "fs";
import path from "path";
import yaml from "js-yaml";
import type { Scenario } from "@/lib/types";

// Reads target_data/scenarios.yaml and maps to Scenario[].
// Container: scenarios.yaml is COPY'd to /app/target_data (Dockerfile.web).
// Local dev (cwd=web/): set SCENARIOS_PATH=../target_data/scenarios.yaml.
// Graceful empty list on miss.

type RawScenario = {
  id: string;
  name: string;
  owasp_llm_top10?: string;
  attack_vector?: string;
  trigger_query?: string;
  expected_block_layer?: string;
  severity?: string;
  canary_token?: string | null;
  canary_extra?: string[];
  recommended_role?: string;
  recommended_guards?: string;
  hint?: string;
};

export async function GET() {
  // In the Docker image scenarios.yaml is COPY'd to /app/target_data (cwd=/app).
  // For local `npm run dev` (cwd=web/), set SCENARIOS_PATH=../target_data/scenarios.yaml.
  const p =
    process.env.SCENARIOS_PATH || path.join(process.cwd(), "target_data", "scenarios.yaml");
  try {
    const doc = yaml.load(await fs.readFile(p, "utf-8")) as { scenarios?: RawScenario[] };
    const scenarios: Scenario[] = (doc?.scenarios ?? []).map((s) => ({
      id: s.id,
      name: s.name,
      owasp: s.owasp_llm_top10 ?? "",
      attack_vector: s.attack_vector ?? "",
      trigger_query: s.trigger_query ?? "",
      expected_block_layer: s.expected_block_layer ?? "",
      severity: s.severity ?? "",
      canary: s.canary_token ?? null,
      canary_extra: s.canary_extra ?? [],
      recommendedRole: (s.recommended_role as Scenario["recommendedRole"]) ?? "user",
      recommendedGuards: s.recommended_guards === "on" ? "on" : "off",
      hint: s.hint ?? "",
    }));
    return Response.json({ scenarios });
  } catch (e) {
    return Response.json({ scenarios: [], error: String(e) });
  }
}
