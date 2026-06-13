"use client";

import { useApp } from "./AppState";
import { ROLE_META } from "@/lib/meta";
import type { Role } from "@/lib/types";

const ROLES: Role[] = ["anonymous", "user", "admin"];

export function RoleSelector() {
  const { role, setRole } = useApp();
  return (
    <div className="flex items-center gap-1 rounded-lg border border-border bg-surface p-0.5">
      {ROLES.map((r) => {
        const m = ROLE_META[r];
        const Icon = m.icon;
        const active = role === r;
        return (
          <button
            key={r}
            onClick={() => setRole(r)}
            title={m.access}
            className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition ${
              active ? "bg-white/10 text-fg" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{m.label}</span>
          </button>
        );
      })}
    </div>
  );
}
