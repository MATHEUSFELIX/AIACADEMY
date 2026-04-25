"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";
import { StepperBar } from "@/components/ui/StepperBar";
import { HookSection } from "@/components/lesson/HookSection";
import { WidgetSection } from "@/components/lesson/WidgetSection";
import { KbSection } from "@/components/lesson/KbSection";
import { ExerciseSection } from "@/components/lesson/ExerciseSection";

interface LessonDetail {
  id: string;
  title: string;
  subtitle: string | null;
  level_number?: number;
  xp_reward?: number;
  duration_min?: number;
  hook_config: Record<string, unknown>;
  widget_config: Record<string, unknown>;
  kb_content: Record<string, unknown>;
}

type Step = "hook" | "widget" | "kb" | "exercise";

const STEPS: { key: Step; label: string }[] = [
  { key: "hook", label: "Hook" },
  { key: "widget", label: "Widget" },
  { key: "kb", label: "KB" },
  { key: "exercise", label: "Exercício" },
];

export default function LessonPage() {
  const params = useParams();
  const id = String(params.id);

  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [step, setStep] = useState<Step>("hook");
  const [unlockedMax, setUnlockedMax] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const key = `lesson:${id}:unlock`;
    try {
      const raw = sessionStorage.getItem(key);
      if (raw !== null) {
        const n = parseInt(raw, 10);
        if (!Number.isNaN(n) && n >= 0 && n <= 3) setUnlockedMax(n);
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
        if (!cancelled) setLesson(json);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof ApiError ? e.message : "Erro ao carregar aula.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  function unlock(targetIdx: number) {
    setUnlockedMax((u) => Math.max(u, targetIdx));
  }

  function completeHook() {
    unlock(1);
    setStep("widget");
  }
  function completeWidget() {
    unlock(2);
    setStep("kb");
  }
  function completeKb() {
    unlock(3);
    setStep("exercise");
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-900/40 bg-red-950/20 px-4 py-3 text-red-300">
        {error}
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="flex flex-col gap-6">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-slate-800" />
        <div className="h-12 animate-pulse rounded-xl bg-slate-800/70" />
        <div className="h-64 animate-pulse rounded-2xl bg-slate-800/50" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 animate-fade-in">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400/80">
          {lesson.level_number != null ? `Nível ${lesson.level_number}` : lesson.id}
        </p>
        <h1 className="mt-1.5 text-2xl font-semibold tracking-tight">
          {lesson.title}
        </h1>
        {lesson.subtitle && (
          <p className="mt-2 text-slate-400">{lesson.subtitle}</p>
        )}
        {(lesson.duration_min || lesson.xp_reward) && (
          <div className="mt-3 flex gap-3">
            {lesson.duration_min && (
              <span className="rounded-full bg-slate-800/80 px-2.5 py-1 text-xs text-slate-400">
                ~{lesson.duration_min} min
              </span>
            )}
            {lesson.xp_reward && (
              <span className="rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-400 ring-1 ring-amber-500/20">
                {lesson.xp_reward} XP
              </span>
            )}
          </div>
        )}
      </div>

      <StepperBar
        steps={STEPS}
        current={step}
        unlockedMax={unlockedMax}
        onChange={(k) => setStep(k as Step)}
      />

      {step === "hook" && (
        <HookSection config={lesson.hook_config} onContinue={completeHook} />
      )}
      {step === "widget" && (
        <WidgetSection config={lesson.widget_config} onContinue={completeWidget} />
      )}
      {step === "kb" && (
        <KbSection content={lesson.kb_content} onContinue={completeKb} />
      )}
      {step === "exercise" && <ExerciseSection lessonId={lesson.id} />}
    </div>
  );
}
