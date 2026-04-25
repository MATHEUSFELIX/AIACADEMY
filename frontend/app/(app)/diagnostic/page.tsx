"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";
import { ChatBubble } from "@/components/diagnostic/ChatBubble";

interface StartResp {
  session_id: string;
  message: string;
  block: string;
}

export default function DiagnosticPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<{ role: string; text: string }[]>(
    [],
  );
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function getToken(): Promise<string> {
    const t = await getAuthToken();
    if (!t) throw new Error("Sem sessão");
    return t;
  }

  async function start() {
    setError(null);
    setLoading(true);
    try {
      const token = await getToken();
      const res = await apiFetch<StartResp>("/diagnostic/start", token, {
        method: "POST",
        body: "{}",
      });
      setSessionId(res.session_id);
      setMessages([{ role: "assistant", text: res.message }]);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Não foi possível iniciar.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function sendAnswer() {
    if (!sessionId || !input.trim()) return;
    setError(null);
    setLoading(true);
    const userLine = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", text: userLine }]);
    try {
      const token = await getToken();
      const res = await apiFetch<{
        type: string;
        message?: string;
        identified_level?: string;
      }>("/diagnostic/answer", token, {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, answer: userLine }),
      });
      const assistantText = res.message ?? "";
      if (res.type === "completed") {
        setDone(res.identified_level || "concluído");
        if (assistantText)
          setMessages((m) => [...m, { role: "assistant", text: assistantText }]);
      } else if (assistantText) {
        setMessages((m) => [...m, { role: "assistant", text: assistantText }]);
      }
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Erro ao enviar resposta.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendAnswer();
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 animate-fade-in">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-400/80">
          Avaliação inicial
        </p>
        <h1 className="mt-1.5 text-2xl font-semibold tracking-tight">
          Diagnóstico
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">
          Conversa guiada pelo BrainAgent para identificar seu nível atual
          (blocos A–D, 10-15 min).
        </p>
      </div>

      {error && (
        <p className="rounded-lg border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      )}

      {done && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/25 px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400/80 mb-1">
            Diagnóstico concluído
          </p>
          <p className="text-emerald-200">
            Nível identificado:{" "}
            <strong>
              {done.replace("level_", "Nível ")}
            </strong>
          </p>
        </div>
      )}

      {!sessionId && !done && (
        <button
          className="w-fit rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          disabled={loading}
          onClick={start}
          type="button"
        >
          {loading ? "Iniciando…" : "Iniciar diagnóstico"}
        </button>
      )}

      {messages.length > 0 && (
        <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
          {messages.map((m, i) => (
            <ChatBubble
              key={`${m.role}-${i}`}
              role={m.role as "assistant" | "user"}
              text={m.text}
            />
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="animate-pulse">BrainAgent está digitando…</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {sessionId && !done && (
        <div className="flex flex-col gap-2">
          <textarea
            className="min-h-[96px] w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-sm leading-relaxed text-slate-100 placeholder-slate-600 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/40 transition"
            placeholder="Digite sua resposta… (Ctrl+Enter para enviar)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-600">Ctrl+Enter para enviar</p>
            <button
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
              disabled={loading || !input.trim()}
              onClick={sendAnswer}
              type="button"
            >
              Enviar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
