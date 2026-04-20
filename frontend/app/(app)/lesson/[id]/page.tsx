"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";

interface LessonDetail {
  id: string;
  title: string;
  subtitle: string | null;
  hook_config: Record<string, unknown>;
  widget_config: Record<string, unknown>;
  kb_content: Record<string, unknown>;
}

type Step = "hook" | "widget" | "kb" | "exercise";

const STEP_ORDER: Step[] = ["hook", "widget", "kb", "exercise"];

const STEP_LABELS: Record<Step, string> = {
  hook: "1. Hook",
  widget: "2. Widget",
  kb: "3. KB",
  exercise: "4. Exercício",
};

function stepIndex(s: Step): number {
  return STEP_ORDER.indexOf(s);
}

export default function LessonPage() {
  const params = useParams();
  const id = String(params.id);
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [step, setStep] = useState<Step>("hook");
  /** Índice 0–3: etapas com tab clicável (e anteriores). */
  const [unlockedMax, setUnlockedMax] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const key = `lesson:${id}:unlock`;
    try {
      const raw = sessionStorage.getItem(key);
      if (raw !== null) {
        const n = parseInt(raw, 10);
        if (!Number.isNaN(n) && n >= 0 && n <= 3) {
          setUnlockedMax(n);
        }
      }
    } catch {
      /* ignore */
    }
  }, [id]);

  useEffect(() => {
    try {
      sessionStorage.setItem(`lesson:${id}:unlock`, String(unlockedMax));
    } catch {
      /* ignore */
    }
  }, [id, unlockedMax]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getAuthToken();
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

  function goToStep(s: Step) {
    setStep(s);
  }

  function unlockThrough(targetIndex: number) {
    setUnlockedMax((u) => Math.max(u, targetIndex));
  }

  function completeHook() {
    unlockThrough(1);
    goToStep("widget");
  }

  function completeWidget() {
    unlockThrough(2);
    goToStep("kb");
  }

  function completeKb() {
    unlockThrough(3);
    goToStep("exercise");
  }

  if (error) {
    return <p className="text-red-400">{error}</p>;
  }
  if (!lesson) {
    return <p className="text-slate-400">Carregando aula…</p>;
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="text-sm uppercase tracking-wide text-slate-500">{lesson.id}</p>
        <h1 className="mt-1 text-2xl font-semibold">{lesson.title}</h1>
        {lesson.subtitle ? <p className="mt-2 text-slate-400">{lesson.subtitle}</p> : null}
      </div>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Etapas da aula">
        {STEP_ORDER.map((s) => {
          const idx = stepIndex(s);
          const active = step === s;
          const locked = idx > unlockedMax;
          return (
            <button
              aria-current={active ? "true" : undefined}
              aria-disabled={locked}
              className={`rounded-full px-3 py-1 text-sm font-medium transition ${
                locked
                  ? "cursor-not-allowed bg-slate-900 text-slate-600 ring-1 ring-slate-800"
                  : active
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
              key={s}
              disabled={locked}
              onClick={() => {
                if (!locked) {
                  goToStep(s);
                }
              }}
              title={locked ? "Conclua a etapa anterior para desbloquear" : undefined}
              type="button"
            >
              {STEP_LABELS[s]}
            </button>
          );
        })}
      </div>
      {step === "hook" ? (
        <HookSection config={lesson.hook_config} onContinue={completeHook} />
      ) : step === "widget" ? (
        <WidgetSection config={lesson.widget_config} onContinue={completeWidget} />
      ) : step === "kb" ? (
        <KbSection content={lesson.kb_content} onContinue={completeKb} />
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

function HookSection({
  config,
  onContinue,
}: {
  config: Record<string, unknown>;
  onContinue: () => void;
}) {
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
      <div className="mt-8 border-t border-slate-800 pt-6">
        <button
          className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-500"
          onClick={onContinue}
          type="button"
        >
          Continuar
        </button>
        <p className="mt-3 text-xs text-slate-500">
          Ao continuar, o widget abre automaticamente na próxima etapa.
        </p>
      </div>
    </Section>
  );
}

function WidgetSection({
  config,
  onContinue,
}: {
  config: Record<string, unknown>;
  onContinue: () => void;
}) {
  const reveal = config.reveal_button as { label?: string } | undefined;
  return (
    <Section title="Widget interativo">
      <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-300">
        {JSON.stringify(config, null, 2)}
      </pre>
      {reveal?.label ? (
        <p className="mt-4 text-xs text-slate-500">
          Interaja com o cenário acima quando fizer sentido (ex.: &quot;{reveal.label}&quot;).
        </p>
      ) : null}
      <div className="mt-8 border-t border-slate-800 pt-6">
        <button
          className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-500"
          onClick={onContinue}
          type="button"
        >
          Continuar para a KB
        </button>
      </div>
    </Section>
  );
}

function KbSection({
  content,
  onContinue,
}: {
  content: Record<string, unknown>;
  onContinue: () => void;
}) {
  return (
    <Section title="Knowledge base">
      <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-300">
        {JSON.stringify(content, null, 2)}
      </pre>
      <div className="mt-8 border-t border-slate-800 pt-6">
        <button
          className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-500"
          onClick={onContinue}
          type="button"
        >
          Continuar para o exercício
        </button>
      </div>
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
      const token = await getAuthToken();
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
      const token = await getAuthToken();
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
