import { Suspense } from "react";
import { ChatPanel } from "@/components/chat/ChatPanel";

export default function ConsolePage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Console / Playground</h1>
        <p className="text-sm text-slate-400">
          Используй ассистента или атакуй его — вердикт по каждому ответу показывает, какой слой сработал.
        </p>
      </div>
      <Suspense fallback={<div className="text-sm text-slate-500">Загрузка…</div>}>
        <ChatPanel />
      </Suspense>
    </div>
  );
}
