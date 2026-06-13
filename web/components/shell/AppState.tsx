"use client";

import { createContext, useContext, useEffect, useState, useCallback, useRef, ReactNode } from "react";
import type { Role, SystemStatus } from "@/lib/types";
import { getStatus, toggleGuards, MOCK_MODE } from "@/lib/api";

type AppState = {
  role: Role;
  setRole: (r: Role) => void;
  guardrailsEnabled: boolean;
  status: SystemStatus | null;
  toggleBusy: boolean;
  handleToggle: () => Promise<void>;
  refresh: () => Promise<void>;
  applyChallengeEnv: (r: Role, guards: "on" | "off") => Promise<void>;
};

const Ctx = createContext<AppState | null>(null);

export const useApp = (): AppState => {
  const c = useContext(Ctx);
  if (!c) throw new Error("useApp must be used within AppStateProvider");
  return c;
};

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>("user");
  const [guardrailsEnabled, setGuards] = useState(true);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [toggleBusy, setToggleBusy] = useState(false);
  const mounted = useRef(0);

  useEffect(() => {
    if (!mounted.current) mounted.current = Date.now();
  }, []);

  const refresh = useCallback(async () => {
    if (MOCK_MODE) {
      const uptime = Math.max(0, Math.round((Date.now() - mounted.current) / 1000));
      setStatus((prev) => ({
        guardrails_enabled: prev?.guardrails_enabled ?? true,
        version: "0.2.0-mock",
        guardrails_runtime: "mock",
        uptime_seconds: uptime,
        chat_model: "granite4.1:8b",
        embedding_model: "bge-m3",
      }));
      return;
    }
    try {
      const s = await getStatus();
      setStatus(s);
      setGuards(Boolean(s.guardrails_enabled));
    } catch {
      setStatus({ guardrails_enabled: true, version: "dev", guardrails_runtime: "unknown" });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (MOCK_MODE) return;
    const t = setInterval(() => void refresh(), 30_000);
    return () => clearInterval(t);
  }, [refresh]);

  const handleToggle = useCallback(async () => {
    if (role !== "admin" || toggleBusy) return;
    if (MOCK_MODE) {
      setGuards((v) => !v);
      return;
    }
    setToggleBusy(true);
    try {
      const s = await toggleGuards(role, !guardrailsEnabled);
      setGuards(Boolean(s.guardrails_enabled));
      setStatus(s);
    } catch {
      void refresh();
    } finally {
      setToggleBusy(false);
    }
  }, [role, toggleBusy, guardrailsEnabled, refresh]);

  // SP1: when a challenge opens, set its recommended role + flip guards to the
  // recommended state. The guards flip always authenticates as admin (control
  // plane) regardless of the attack role we set for the player.
  const applyChallengeEnv = useCallback(async (r: Role, guards: "on" | "off") => {
    setRole(r);
    const wantEnabled = guards === "on";
    if (MOCK_MODE) {
      setGuards(wantEnabled);
      return;
    }
    try {
      const s = await toggleGuards("admin", wantEnabled);
      setGuards(Boolean(s.guardrails_enabled));
      setStatus(s);
    } catch {
      void refresh();
    }
  }, [refresh]);

  return (
    <Ctx.Provider value={{ role, setRole, guardrailsEnabled, status, toggleBusy, handleToggle, refresh, applyChallengeEnv }}>
      {children}
    </Ctx.Provider>
  );
}
