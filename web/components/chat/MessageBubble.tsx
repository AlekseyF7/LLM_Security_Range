"use client";

import DOMPurify from "isomorphic-dompurify";
import { Copy, ExternalLink } from "lucide-react";
import { VerdictChip } from "./VerdictChip";
import { RbacChip } from "./RbacChip";
import type { ChatMessage } from "@/lib/types";

// IMPORTANT: keep ALLOWED_ATTR empty. A RAG-injection could otherwise build a
// fake "GUARD OK" overlay from tailwind classes already in the bundle and
// visually deceive the user. Tags whitelist is intentionally minimal.
const SANITIZE = {
  ALLOWED_TAGS: ["b", "i", "u", "p", "br", "code", "pre", "ul", "ol", "li", "strong", "em"],
  ALLOWED_ATTR: [] as string[],
};

export function MessageBubble({ msg, langfuseBase }: { msg: ChatMessage; langfuseBase: string }) {
  const isUser = msg.role === "user";
  const isBlocked = !isUser && Boolean(msg.blocked);
  const isErrored = !isUser && Boolean(msg.errored);
  const showGuardFooter = !isUser && Boolean(msg.guardMessage) && !isErrored;
  const showRbac = !isUser && Boolean(msg.rbac?.filtered) && (msg.rbac?.hidden ?? 0) > 0;
  const __html = DOMPurify.sanitize(msg.content, SANITIZE);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[85%] flex-col ${isUser ? "items-end" : "items-start"}`}>
        {!isUser && (isBlocked || isErrored || showRbac) && (
          <div className="mb-1 flex flex-wrap items-center gap-1.5">
            {(isBlocked || isErrored) && (
              <VerdictChip layer={msg.layer ?? null} blocked={msg.blocked} errored={msg.errored} httpStatus={msg.httpStatus} />
            )}
            {showRbac && msg.rbac && <RbacChip rbac={msg.rbac} />}
          </div>
        )}

        <div
          className={`rounded-2xl px-4 py-2.5 text-sm ${
            isUser
              ? "bg-accent text-slate-900"
              : isBlocked
                ? "border border-bad/40 bg-bad/10 text-rose-100"
                : isErrored
                  ? "border border-warn/30 bg-white/5 text-slate-300"
                  : "border border-border bg-white/5 text-slate-200"
          }`}
        >
          <div className="whitespace-pre-wrap break-words" dangerouslySetInnerHTML={{ __html }} />
          {showGuardFooter && (
            <div
              className={`mt-2 border-t pt-2 text-[11px] italic ${
                isBlocked ? "border-bad/30 text-rose-300/80" : "border-border text-slate-400"
              }`}
            >
              guard: {msg.guardMessage}
            </div>
          )}
        </div>

        <div className={`mt-1 flex items-center gap-2 text-[10px] text-slate-500 ${isUser ? "flex-row-reverse" : ""}`}>
          <span>
            {msg.timestamp.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </span>
          {!isUser && (
            <>
              <button
                onClick={() => void navigator.clipboard.writeText(msg.content).catch(() => {})}
                className="transition hover:text-slate-300"
                title="Скопировать ответ"
              >
                <Copy className="h-3 w-3" />
              </button>
              {msg.traceId && (
                <a
                  href={`${langfuseBase}/trace/${msg.traceId}`}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 transition hover:text-accent"
                  title="Трейс в Langfuse"
                >
                  <ExternalLink className="h-3 w-3" /> trace
                </a>
              )}
              {msg.httpStatus ? <span className="font-mono opacity-70">HTTP {msg.httpStatus}</span> : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
