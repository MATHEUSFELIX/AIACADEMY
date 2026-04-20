"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";

interface StartResp {
  session_id: string;
  message: string;
  block: string;
}

export default function DiagnosticPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    // no auto-start — usuário clica para começar
  }, []);

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
      const res = await apiFetch<StartResp>("/diagnostic/start", token, { method: "POST", body: "{}" });
      setSessionId(res.session_id);
      setMessages([{ role: "assistant", text: res.message }]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Não foi possível iniciar.");
    } finally {
      setLoading(false);
    }
  }

  async function sendAnswer() {
    if (!sessionId || !input.trim()) {
      return;
    }
    setError(null);
    setLoading(true);
    const userLine = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", text: userLine }]);
    try {
      const token = await getToken();
      const res = await apiFetch<{ type: string; message?: string; identified_level?: string }>(
        "/diagnostic/answer",
        token,
        {
          method: "POST",
          body: JSON.stringify({ session_id: sessionId, answer: userLine }),
        },
      );
      const assistantText = res.message ?? "";
      if (res.type === "completed") {
        setDone(res.identified_level || "concluído");
        if (assistantText) {
          setMessages((m) => [...m, { role: "assistant", text: assistantText }]);
        }
      } else if (assistantText) {
        setMessages((m) => [...m, { role: "assistant", text: assistantText }]);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao enviar resposta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <h1 className="text-2xl font-semibold">Diagnóstico</h1>
      <p className="text-slate-400">
        Conversa guiada pelo BrainAgent para estimar seu nível inicial (blocos A–D).
      </p>
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
      {done ? (
        <p className="rounded-lg border border-emerald-800 bg-emerald-950/40 p-4 text-emerald-200">
          Diagnóstico concluído — nível sugerido: <strong>{done}</strong>
        </p>
      ) : null}
      {!sessionId ? (
        <button
          className="w-fit rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          disabled={loading}
          onClick={start}
          type="button"
        >
          {loading ? "Iniciando…" : "Iniciar diagnóstico"}
        </button>
      ) : null}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        {messages.map((m, i) => (
          <div
            className={`text-sm ${m.role === "assistant" ? "text-slate-200" : "text-indigo-300"}`}
            key={`${m.role}-${i}`}
          >
            <span className="font-medium">{m.role === "assistant" ? "BrainAgent" : "Você"}:</span>{" "}
            {m.text}
          </div>
        ))}
      </div>
      {sessionId && !done ? (
        <div className="flex gap-2">
          <textarea
            className="min-h-[96px] flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
            placeholder="Digite sua resposta…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button
            className="self-end rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-white disabled:opacity-50"
            disabled={loading}
            onClick={sendAnswer}
            type="button"
          >
            Enviar
          </button>
        </div>
      ) : null}
    </div>
  );
}
