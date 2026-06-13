import { promises as fs } from "fs";
import path from "path";

// Reads the latest promptfoo results JSON and aggregates pass/fail by OWASP
// category. Path via PROMPTFOO_RESULTS_PATH, else repo-root/promptfoo-results.json.
// Tolerant of promptfoo's version-varying shape; returns {available:false} on miss.

type Row = {
  success?: boolean;
  testCase?: { metadata?: Record<string, unknown> };
  metadata?: Record<string, unknown>;
};

export async function GET() {
  const p = process.env.PROMPTFOO_RESULTS_PATH || path.join(process.cwd(), "..", "promptfoo-results.json");
  try {
    const raw = await fs.readFile(p, "utf-8");
    const json = JSON.parse(raw) as {
      results?: { results?: Row[]; timestamp?: string };
      timestamp?: string;
    };
    const rows: Row[] = json.results?.results ?? (Array.isArray(json.results) ? (json.results as Row[]) : []);

    const byCat = new Map<string, { passed: number; total: number }>();
    let passed = 0;
    for (const r of rows) {
      const ok = Boolean(r.success);
      if (ok) passed++;
      const meta = r.testCase?.metadata ?? r.metadata ?? {};
      const code = String(meta.owasp ?? meta.vector ?? "other");
      const c = byCat.get(code) ?? { passed: 0, total: 0 };
      c.total++;
      if (ok) c.passed++;
      byCat.set(code, c);
    }

    return Response.json({
      available: true,
      ranAt: json.results?.timestamp ?? json.timestamp ?? null,
      total: rows.length,
      passed,
      byCategory: [...byCat].map(([code, v]) => ({ code, ...v })),
    });
  } catch {
    return Response.json({ available: false });
  }
}
