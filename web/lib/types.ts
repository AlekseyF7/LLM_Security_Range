// Shared types for the Smart Wiki web platform.
// Single source of truth — keep in sync with the FastAPI ChatResponse contract.

export type Role = "anonymous" | "user" | "admin";
export type Layer = "L1" | "L2" | "L3" | "L4" | null;

export type RbacInfo = {
  filtered: boolean;
  hidden: number;
  role: string;
};

export type ChatResponse = {
  answer: string;
  blocked?: boolean;
  guard_message?: string | null;
  trace_id?: string | null;
  rbac?: RbacInfo | null;
};

export type SystemStatus = {
  version: string;
  guardrails_enabled: boolean;
  guardrails_runtime?: string;
  uptime_seconds?: number;
  chat_model?: string;
  embedding_model?: string;
};

export type Scenario = {
  id: string;
  name: string;
  owasp: string; // owasp_llm_top10
  attack_vector: string;
  trigger_query: string;
  expected_block_layer: string; // e.g. "L4_output_guard"
  severity: string;
  canary: string | null; // canary_token
  canary_extra?: string[];
  recommendedRole: Role; // SP1: auto-set when challenge opens
  recommendedGuards: "on" | "off"; // SP1: auto-flip guards when challenge opens
  hint: string; // SP1: how-to-pass hint shown in the challenge banner
};

export type Challenge = Scenario & {
  mode: "bypass" | "defense"; // bypass = leak secret/canary; defense = confirm block at layer
};

export type JudgeResult = {
  won: boolean;
  reason: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  blocked?: boolean;
  errored?: boolean; // transport / 500 / shape mismatch — NOT a guard decision
  guardMessage?: string | null;
  layer?: Layer;
  httpStatus?: number;
  traceId?: string | null;
  rbac?: RbacInfo | null;
};
