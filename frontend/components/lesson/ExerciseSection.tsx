"use client";

import { useState } from "react";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";
import { ResultCard } from "./ResultCard";

interface SubmitResponse {
  feedback: string;
  score?: number;
  xp_earned?: number;
}

export function ExerciseSection({ lessonId }: { lessonId: string }) {
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState<string | null>(null);
  const [context, setContext] = useState<string | null>(null);
  const [exerciseId, setExerciseId] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<SubmitResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const token = await getAuthToken();
      if (!token) {
        setError("Sessão expirada.");
        return;
      }
      const res = await apiFetch<{
        exercise_id: string;
        question: string;
        context: string;
      }>(`/lessons/${lessonId}/exercise/generate`, token, { method: "POST" });
      setExerciseId(res.exercise_id);
      setQuestion(res.question);
      setContext(res.context);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao gerar exercício.");
    } finally {
      setLoading(false);
    }
  }

  async function submit() {
    if (!exerciseId) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getAuthToken();
      if (!token) {
        setError("Sessão expirada.");
        return;
      }
      const res = await apiFetch<SubmitResponse>(
        `/lessons/${lessonId}/exercise/submit`,
        token,
        {
          method: "POST",
          body: JSON.stringify({
            exercise_id: exerciseId,
            answer,
            used_hint: false,
          }),
        },
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Erro ao enviar resposta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 animate-fade-in">
      <div className="p-6 sm:p-8">
        <h2 className="text-base font-semibold text-slate-100">Exercício</h2>
        <p className="mt-1 text-sm text-slate-500">
          Personalizado pelo BrainAgent com base no seu perfil e histórico.
        </p>

        {error && (
          <p className="mt-4 rounded-lg border border-red-900/40 bg-red-950/20 px-4 py-3 text-sm text-red-300">
            {error}
          </p>
        )}

        {!question && !result && (
          <div className="mt-6">
            <button
              type="button"
              onClick={generate}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle
                      className="opacity-25"
                      cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Gerando…
                </>
              ) : (
                "Gerar exercício"
              )}
            </button>
          </div>
        )}

        {question && !result && (
          <div className="mt-6 flex flex-col gap-5 animate-fade-in">
            {context && (
              <div className="rounded-lg border border-slate-700/60 bg-slate-950/40 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  Contexto
                </p>
                <p className="text-sm leading-relaxed text-slate-400">{context}</p>
              </div>
            )}

            <p className="text-base leading-relaxed text-slate-100">{question}</p>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Sua resposta
              </label>
              <textarea
                className="min-h-[140px] rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm leading-relaxed text-slate-100 placeholder-slate-600 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/40 transition"
                placeholder="Escreva sua análise…"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
              />
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={submit}
                disabled={loading || !answer.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Avaliando…
                  </>
                ) : (
                  "Enviar para avaliação"
                )}
              </button>
            </div>
          </div>
        )}

        {result && (
          <div className="mt-6">
            <ResultCard
              feedback={result.feedback}
              score={result.score}
              xpEarned={result.xp_earned}
            />
          </div>
        )}
      </div>
    </section>
  );
}
