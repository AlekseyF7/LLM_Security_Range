"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { Send, ShieldCheck } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import { PayloadChips } from "./PayloadChips";
import { ChallengeHint } from "./ChallengeHint";
import { useApp } from "@/components/shell/AppState";
import { chat, MOCK_MODE, resolveApiUrl } from "@/lib/api";
import { useLangfuseBase } from "@/lib/hooks";
import { judge } from "@/lib/judge";
import { markWon } from "@/lib/progress";
import type { ChatMessage, ChatResponse, Layer, Challenge, JudgeResult, Scenario } from "@/lib/types";

function mockClassify(query: string): { blocked: boolean; layer: Layer; status: number; guard: string | null } {
  const isL1 = /ignore|jailbreak|DAN|prompt|system|override|инструкци/i.test(query);
  const isL4 = /пароль|password|снилс|snils|секрет|secret|aws|jwt|api[_-]?key/i.test(query);
  if (isL1) return { blocked: true, layer: "L1", status: 403, guard: "self_check_input (jailbreak intent)." };
  if (isL4) return { blocked: true, layer: "L4", status: 200, guard: "output guard: PII/credentials, ответ переписан." };
  return { blocked: false, layer: null, status: 200, guard: null };
}

export function ChatPanel() {
  const { role, guardrailsEnabled, applyChallengeEnv } = useApp();
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState(() => searchParams.get("payload") ?? "");
  const [isLoading, setIsLoading] = useState(false);
  const [activeChallenge, setActiveChallenge] = useState<Challenge | null>(null);
  const [result, setResult] = useState<JudgeResult | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const lf = useLangfuseBase();

  // Load the challenge def (if ?challenge=) once on mount. Input is seeded
  // from ?payload via the useState initializer above (no setState-in-effect).
  useEffect(() => {
    const challengeId = searchParams.get("challenge");
    if (!challengeId) return;
    fetch("/api/scenarios")
      .then((r) => r.json())
      .then((d: { scenarios: Scenario[] }) => {
        const s = (d.scenarios ?? []).find((x) => x.id === challengeId);
        if (s) {
          setActiveChallenge({ ...s, mode: "bypass" });
          setInput((prev) => (prev ? prev : s.trigger_query));
          // SP1: auto-apply the challenge's recommended role + guards state.
          void applyChallengeEnv(s.recommendedRole, s.recommendedGuards);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const append = (msg: ChatMessage) => setMessages((p) => [...p, msg]);

  const runJudge = (resp: ChatResponse, layer: Layer) => {
    if (!activeChallenge) return;
    const jr = judge(activeChallenge, resp, layer);
    setResult(jr);
    if (jr.won) markWon(activeChallenge.id);
  };

  const send = async (query: string) => {
    if (!query.trim() || isLoading) return;
    append({ id: crypto.randomUUID(), role: "user", content: query, timestamp: new Date() });
    setInput("");
    setIsLoading(true);

    if (MOCK_MODE) {
      setTimeout(() => {
        const m = mockClassify(query);
        const content = m.blocked
          ? "[MOCK] Запрос заблокирован защитой."
          : `[MOCK] Ответ как ${role}. Guards: ${guardrailsEnabled ? "ON" : "OFF"}.`;
        append({
          id: crypto.randomUUID(),
          role: "assistant",
          content,
          timestamp: new Date(),
          blocked: m.blocked,
          layer: m.layer,
          guardMessage: m.guard,
          httpStatus: m.status,
        });
        runJudge({ answer: content, blocked: m.blocked, guard_message: m.guard }, m.layer);
        setIsLoading(false);
      }, 500);
      return;
    }

    try {
      const { data, httpStatus, layer, errored } = await chat(query, role);
      append({
        id: crypto.randomUUID(),
        role: "assistant",
        content: errored
          ? data.guard_message || `Ошибка backend: HTTP ${httpStatus}`
          : data.answer || (data.blocked ? "Ответ заблокирован защитой." : "(пустой ответ)"),
        timestamp: new Date(),
        blocked: Boolean(data.blocked),
        errored,
        guardMessage: data.guard_message ?? null,
        layer,
        httpStatus,
        traceId: data.trace_id ?? null,
        rbac: data.rbac ?? null,
      });
      if (!errored) runJudge(data, layer);
    } catch (err) {
      const m = err instanceof Error ? err.message : String(err);
      append({
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Ошибка соединения с API (${resolveApiUrl()}): ${m}. Проверь, что FastAPI запущен и порт 8000 открыт.`,
        timestamp: new Date(),
        errored: true,
        layer: null,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  return (
    <div className="flex h-[calc(100vh-220px)] min-h-[480px] flex-col rounded-xl border border-border bg-surface">
      {activeChallenge && (
        <div className="border-b border-accent/30 bg-accent/5 px-4 py-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-mono text-accent">Challenge {activeChallenge.id}</span>
            <span className="text-slate-500">{activeChallenge.owasp}</span>
          </div>
          <div className="mt-0.5 text-slate-300">{activeChallenge.name}</div>
          <ChallengeHint challenge={activeChallenge} />
          <div className="text-slate-500">
            Цель: вытащи секрет / обойди защиту (guards {guardrailsEnabled ? "ON" : "OFF"}).
          </div>
          {result && (
            <div className={`mt-1 font-medium ${result.won ? "text-ok" : "text-warn"}`}>
              {result.won ? "✓ Пройдено!" : "✗ Пока нет"} — {result.reason}
            </div>
          )}
        </div>
      )}

      <div className="scroll-thin flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <ShieldCheck className="h-14 w-14 text-accent/40" />
            <div>
              <h2 className="text-xl font-semibold text-slate-200">Готов принять запрос</h2>
              <p className="mt-1 max-w-md text-sm text-slate-500">
                Обычный вопрос или готовый payload-сценарий — и смотри, какой слой защиты сработает.
              </p>
            </div>
            <PayloadChips onPick={(q) => void send(q)} />
            <p className="text-[10px] text-slate-600">Все «секреты» в базе — фейковые тест-фикстуры.</p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} msg={m} langfuseBase={lf} />
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl border border-border bg-white/5 px-4 py-3 text-sm">
              <span className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" style={{ animationDelay: "150ms" }} />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" style={{ animationDelay: "300ms" }} />
              </span>
              <span className="text-xs text-slate-400">
                обработка через {guardrailsEnabled ? "L1 → agent → L4" : "agent (no guards)"}
              </span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {messages.length > 0 && (
        <div className="scroll-thin flex gap-1.5 overflow-x-auto border-t border-border px-3 py-2">
          <PayloadChips onPick={(q) => void send(q)} />
        </div>
      )}

      <form onSubmit={onSubmit} className="flex gap-2 border-t border-border p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
          autoFocus
          placeholder={
            role === "anonymous"
              ? "Запрос как гость (только публичные документы)…"
              : role === "admin"
                ? "Запрос как админ (полный доступ + toggle защиты)…"
                : "Введите запрос или выберите сценарий ниже…"
          }
          className="flex-1 rounded-lg border border-border bg-white/5 px-3 py-2 text-sm placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/50"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="flex items-center gap-2 rounded-lg bg-accent px-4 text-sm font-medium text-slate-900 transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send className="h-4 w-4" /> <span className="hidden sm:inline">Отправить</span>
        </button>
      </form>
    </div>
  );
}
