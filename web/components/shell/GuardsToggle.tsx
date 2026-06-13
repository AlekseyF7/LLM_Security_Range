"use client";

import { ShieldCheck, ShieldOff } from "lucide-react";
import { useApp } from "./AppState";

export function GuardsToggle() {
  const { role, guardrailsEnabled, toggleBusy, handleToggle } = useApp();
  const isAdmin = role === "admin";
  return (
    <div
      className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 ${
        guardrailsEnabled ? "border-ok/30 bg-ok/10" : "border-warn/30 bg-warn/10"
      }`}
    >
      {guardrailsEnabled ? (
        <ShieldCheck className="h-4 w-4 text-ok" />
      ) : (
        <ShieldOff className="h-4 w-4 text-warn" />
      )}
      <span className="text-xs font-medium">{guardrailsEnabled ? "GUARDS ON" : "GUARDS OFF"}</span>
      <button
        onClick={() => void handleToggle()}
        disabled={!isAdmin || toggleBusy}
        title={isAdmin ? "Переключить (admin)" : "Доступно только админу"}
        className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
          guardrailsEnabled ? "bg-ok" : "bg-warn"
        } ${isAdmin ? "cursor-pointer hover:opacity-90" : "cursor-not-allowed opacity-30"}`}
      >
        <span
          className={`h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${
            guardrailsEnabled ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}
