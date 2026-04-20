"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getSupabase } from "@/lib/supabase";
import { apiFetch, ApiError } from "@/lib/api";

interface LessonDetail {
  id: string;
  title: string;
  subtitle: string | null;
  hook_config: Record<string, unknown>;
  widget_config: Record<string, unknown>;
  kb_content: Record<string, unknown>;
}

type Step = "hook" | "widget" | "kb" | "exercise";

export default function LessonPage() {
  const params = useParams();
  const id = String(params.id);
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [step, setStep] = useState<Step>("hook");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const supabase = getSupabase();
        const { data } = await supabase.auth.getSession();
        const token = data.session?.access_token;
        if (!token) {
          setError("Faça login.");
          return;
        }
        const json = await apiFetch<LessonDetail>(`/lessons/${id}`, token);
        await apiFetch(`/lessons/${id}/start`, token, { method: "POST" });
        if (!cancelled) {
          setLesson(json);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Erro ao carregar aula.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return <p className="text-red-400">{error}</p>;
  }
  if (!lesson) {
    return <p className="text-slate-400">Carregando aula…</p>;
  }

  const steps: { key: Step; label: string }[] = [
    { key: "hook", label: "1. Hook" },
    { key: "widget", label: "2. Widget" },
    { key: "kb", label: "3. KB" },
    { key: "exercise", label: "4. Exercício" },
  ];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="text-sm uppercase tracking-wide text-slate-500">{lesson.id}</p>
        <h1 className="mt-1 text-2xl font-semibold">{lesson.title}</h1>
        {lesson.subtitle ? <p className="mt-2 text-slate-400">{lesson.subtitle}</p> : null}
      </div>
      <div className="flex flex-wrap gap-2">
        {steps.map((s) => (
          <button
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              step === s.key
                ? "bg-indigo-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
            key={s.key}
            onClick={() => setStep(s.key)}
            type="button"
          >
            {s.label}
          </button>
        ))}
      </div>
      {step === "hook" ? (
        <HookSection config={lesson.hook_config} />
      ) : step === "widget" ? (
        <Section title="Widget interativo">
          <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-300">
            {JSON.stringify(lesson.widget_config, null, 2)}
          </pre>
        </Section>
      ) : step === "kb" ? (
        <Section title="Knowledge base">
          <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-300">
            {JSON.stringify(lesson.kb_content, null, 2)}
          </pre>
        </Section>
      ) : (
        <ExerciseSection lessonId={lesson.id} />
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
      <h2 className="text-lg font-medium">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function HookSection({ config }: { config: Record<string, unknown> }) {
  const scenes = (config.scenes as { text?: string; sub?: string }[] | undefined) || [];
  return (
    <Section title="Hook — cenário">
      <ul className="space-y-4">
        {scenes.map((s, i) => (
          <li className="rounded-lg border border-slate-800 bg-slate-950/50 p-4" key={i}>
            {s.sub ? <p className="text-xs uppercase text-slate-500">{s.sub}</p> : null}
            <p className="mt-2 text-slate-200">{s.text}</p>
          </li>
        ))}
      </ul>
      {typeof config.cta === "string" ? (
        <p className="mt-6 text-sm text-indigo-400">{config.cta}</p>
      ) : null}
    </Section>
  );
}

function ExerciseSection({ lessonId }: { lessonId: string }) {
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState<string | null>(null);
  const [context, setContext] = useState<string | null>(null);
  const [exerciseId, setExerciseId] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setFeedback(null);
    try {
      const supabase = getSupabase();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
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
      setFeedback(e instanceof Error ? e.message : "Erro");
    } finally {
      setLoading(false);
    }
  }

  async function submit() {
    if (!exerciseId) {
      return;
    }
    setLoading(true);
    try {
      const supabase = getSupabase();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        return;
      }
      const res = await apiFetch<{ feedback: string }>(`/lessons/${lessonId}/exercise/submit`, token, {
        method: "POST",
        body: JSON.stringify({
          exercise_id: exerciseId,
          answer,
          used_hint: false,
        }),
      });
      setFeedback(res.feedback);
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Erro ao enviar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section title="Exercício">
      {!question ? (
        <button
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          disabled={loading}
          onClick={generate}
          type="button"
        >
          {loading ? "Gerando…" : "Gerar exercício (BrainAgent)"}
        </button>
      ) : (
        <div className="flex flex-col gap-4">
          {context ? <p className="text-sm text-slate-400">{context}</p> : null}
          <p className="text-slate-100">{question}</p>
          <textarea
            className="min-h-[120px] rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            placeholder="Sua resposta…"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          <button
            className="w-fit rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
            disabled={loading}
            onClick={submit}
            type="button"
          >
            Enviar para avaliação
          </button>
        </div>
      )}
      {feedback ? (
        <p className="mt-4 whitespace-pre-wrap rounded-lg border border-slate-700 bg-slate-950 p-4 text-sm text-slate-200">
          {feedback}
        </p>
      ) : null}
    </Section>
  );
}
