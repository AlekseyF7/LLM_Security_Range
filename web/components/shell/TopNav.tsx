"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck, Activity, ExternalLink } from "lucide-react";
import { RoleSelector } from "./RoleSelector";
import { GuardsToggle } from "./GuardsToggle";
import { LayerStrip } from "./LayerStrip";
import { useLangfuseBase } from "@/lib/hooks";

const LINKS = [
  { href: "/", label: "Главная" },
  { href: "/console", label: "Console" },
  { href: "/lab", label: "Lab" },
  { href: "/dashboard", label: "Dashboard" },
];

export function TopNav() {
  const pathname = usePathname();
  const lf = useLangfuseBase();

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-bg/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 lg:flex-row lg:items-center lg:justify-between lg:px-6">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-accent" />
            <span className="text-lg font-bold leading-tight">Smart Wiki</span>
          </Link>
          <nav className="flex items-center gap-1">
            {LINKS.map((l) => {
              const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-md px-2.5 py-1 text-sm transition ${
                    active ? "bg-white/10 text-fg" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <LayerStrip />
          <RoleSelector />
          <GuardsToggle />
          <a
            href={lf}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-xs text-slate-400 transition hover:text-accent"
            title="Открыть Langfuse"
          >
            <Activity className="h-3.5 w-3.5" /> Langfuse <ExternalLink className="h-3 w-3 opacity-60" />
          </a>
        </div>
      </div>
    </header>
  );
}
