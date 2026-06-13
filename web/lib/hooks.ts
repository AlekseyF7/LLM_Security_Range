import { useSyncExternalStore } from "react";
import { langfuseBase, resolveApiUrl } from "./api";

/**
 * Langfuse base URL derived from window.location. Hydration-safe via
 * useSyncExternalStore: server snapshot = localhost, client snapshot = real
 * host — no setState-in-effect, no hydration mismatch.
 */
export function useLangfuseBase(): string {
  return useSyncExternalStore(
    () => () => {},
    () => langfuseBase(resolveApiUrl()),
    () => "http://localhost:3000",
  );
}
