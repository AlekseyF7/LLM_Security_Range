import Link from "next/link";
import { OWASP_CATALOG } from "@/lib/meta";

export function TechniqueCatalog() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {OWASP_CATALOG.map((t) => (
        <div key={t.code} className="rounded-xl border border-border bg-surface p-4">
          <div className="font-mono text-[11px] text-accent">{t.code}</div>
          <h3 className="mt-1 text-sm font-medium text-slate-200">{t.title}</h3>
          <p className="mt-1 text-xs text-slate-500">{t.desc}</p>
          <Link
            href={`/console?payload=${encodeURIComponent(t.samplePayload)}`}
            className="mt-3 inline-block text-xs text-accent hover:underline"
          >
            Попробовать →
          </Link>
        </div>
      ))}
    </div>
  );
}
