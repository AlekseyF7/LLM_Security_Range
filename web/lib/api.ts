// API client + small helpers for the Smart Wiki backend.
// Logic ported from the original page.tsx; framework-agnostic.

import type { ChatResponse, Layer, Role, SystemStatus } from "./types";

export const resolveApiUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window === "undefined") return "http://localhost:8000";
  return `${window.location.protocol}//${window.location.hostname}:8000`;
};

export const MOCK_MODE = process.env.NEXT_PUBLIC_MOCK_MODE === "true";

export function langfuseBase(apiUrl: string): string {
  try {
    const u = new URL(apiUrl);
    return `${u.protocol}//${u.hostname}:3000`;
  } catch {
    return "http://localhost:3000";
  }
}

/** 200+blocked=L4, 403=L1, 429=L2. L3 (RBAC) never sets blocked. */
export function detectLayer(httpStatus: number, data: ChatResponse): Layer {
  if (!data.blocked) return null;
  if (httpStatus === 403) return "L1";
  if (httpStatus === 429) return "L2";
  if (httpStatus === 200) return "L4";
  return null;
}

export function isChatResponseShape(x: unknown): x is ChatResponse {
  return (
    typeof x === "object" &&
    x !== null &&
    "answer" in x &&
    "blocked" in x &&
    typeof (x as ChatResponse).answer === "string"
  );
}

export function formatUptime(sec?: number): string {
  if (!sec || sec < 0) return "—";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h) return `${h}ч ${m}м`;
  if (m) return `${m}м ${s}с`;
  return `${s}с`;
}

export type ChatResult = {
  data: ChatResponse;
  httpStatus: number;
  layer: Layer;
  errored: boolean;
};

/** Calls the backend, normalizing 200/403/429/500 into one shape (mirrors original page.tsx). */
export async function chat(query: string, role: Role): Promise<ChatResult> {
  const url = `${resolveApiUrl()}/api/v1/chat`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Role": role },
    body: JSON.stringify({ query }),
  });

  let data: ChatResponse;
  let errored = false;

  if (resp.status === 403 || resp.status === 429 || resp.status === 500) {
    const body = await resp.json().catch(() => ({}));
    const detail =
      body && typeof body === "object" && "detail" in body
        ? (body as { detail: unknown }).detail
        : null;
    if (isChatResponseShape(detail)) {
      data = detail;
    } else {
      errored = resp.status === 500;
      data = {
        answer: "",
        blocked: !errored,
        guard_message:
          typeof detail === "string" ? `HTTP ${resp.status}: ${detail}` : `HTTP ${resp.status}`,
      };
    }
  } else if (resp.ok) {
    data = (await resp.json()) as ChatResponse;
  } else {
    errored = true;
    data = { answer: "", blocked: false, guard_message: `HTTP ${resp.status}` };
  }

  return { data, httpStatus: resp.status, layer: detectLayer(resp.status, data), errored };
}

export async function getStatus(): Promise<SystemStatus> {
  const resp = await fetch(`${resolveApiUrl()}/api/v1/system/status`, { cache: "no-store" });
  if (!resp.ok) throw new Error(`status ${resp.status}`);
  return (await resp.json()) as SystemStatus;
}

export async function toggleGuards(role: Role, enabled: boolean): Promise<SystemStatus> {
  const resp = await fetch(`${resolveApiUrl()}/api/v1/system/guardrails`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User-Role": role },
    body: JSON.stringify({ enabled }),
  });
  if (!resp.ok) throw new Error(`toggle ${resp.status}`);
  return getStatus();
}
