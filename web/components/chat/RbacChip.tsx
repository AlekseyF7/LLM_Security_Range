"use client";

import { Lock } from "lucide-react";
import type { RbacInfo } from "@/lib/types";

/** Informational L3/RBAC chip. Shown when role-based filtering dropped chunks.
 *  NOT a block — the user still got an answer from the visible chunks — so the
 *  style is muted (slate), distinct from the red VerdictChip. Count + role only
 *  (no hidden filenames: that would meta-leak which restricted docs exist). */
export function RbacChip({ rbac }: { rbac: RbacInfo }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-white/5 px-2 py-1 text-[11px] text-slate-400">
      <Lock className="h-3 w-3" />
      <span className="font-mono font-bold">L3</span> · скрыто {rbac.hidden}
      <span className="opacity-60">(роль: {rbac.role})</span>
    </span>
  );
}
