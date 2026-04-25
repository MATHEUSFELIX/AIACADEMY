"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Badge } from "@/components/ui/Badge";
import type { StudentMe } from "@/lib/types";

interface Overview {
  next_lesson: {
    id: string;
    title: string;
    level_number: number;
    xp_reward: number;
    duration_min: number;
  } | null;
  brainagent_message: string;
  current_level: {
    level: string;
    progress_pct: number;
    lessons_done: number;
    lessons_total: number;
  };
  recent_activity?: Array<{
    lesson_id: string;
    title: string;
    score: number | null;
    completed_at: string | null;
  }>;
}

interface LessonRow {
  id: string;
  title: string;
  module: string;
  level_number: number;
  xp_reward: number;
  duration_min: number;
  status: string;
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [me, setMe] = useState<StudentMe | null>(null);
  const [lessons, setLessons] = useState<LessonRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getAuthToken();
        if (!token) {
          setError("Faça login para ver o painel.");
          return;
        }
        const [ov, profile, ls] = await Promise.all([
          apiFetch<Overview>("/students/me/overview", token),
          apiFetch<StudentMe>("/students/me", token),
          apiFetch<{ lessons: LessonRow[] }>("/lessons", token),
        ]);
        if (!cancelled) {
          setOverview(ov);
          setMe(profile);
          setLessons(ls.lessons);
        }
      } catch (e) {
        if (!cancelled)
          setError(
            e instanceof ApiError ? e.message : "Falha ao carregar painel.",
          );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-xl border border-red-900/40 bg-red-950/25 px-4 py-3 text-red-300">
        {error}{" "}
        <Link className="font-medium text-indigo-400 underline" href="/login">
          Ir para login
        </Link>
      </div>
    );
  }

  if (!overview || !me) {
    return (
      <div className="flex flex-col gap-6">
        <div className="h-10 w-56 animate-pulse rounded-lg bg-slate-800" />
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="h-36 animate-pulse rounded-2xl bg-slate-800/80 lg:col-span-2" />
          <div className="h-36 animate-pulse rounded-2xl bg-slate-800/60" />
        </div>
        <div className="h-52 animate-pulse rounded-xl bg-slate-800/60" />
      </div>
    );
  }

  const firstName = me.name ? me.name.split(" ")[0] : "";
  const levelLabel = overview.current_level.level.replace("level_", "Nível ");

  return (
    <div className="flex flex-col gap-8 animate-fade-in">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl border border-indigo-500/25 bg-gradient-to-br from-indigo-950/90 via-slate-900 to-slate-950 p-6 shadow-xl shadow-indigo-950/60 sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-10 left-1/3 h-32 w-32 rounded-full bg-violet-600/10 blur-2xl" />

        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-300/80">
              Painel
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
              {firstName ? `Olá, ${firstName}` : "Olá"}
            </h1>
            {overview.brainagent_message && (
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-400">
                {overview.brainagent_message}
              </p>
            )}
          </div>

          <div className="flex flex-wrap gap-3">
            <StatPill
              label="XP total"
              value={String(me.total_xp ?? 0)}
              colorClass="from-amber-500/20 to-amber-950/40 border-amber-500/20"
              textClass="text-amber-300"
            />
            <StatPill
              label="Sequência"
              value={`${me.streak_days ?? 0} dias`}
              colorClass="from-emerald-500/15 to-emerald-950/30 border-emerald-500/20"
              textClass="text-emerald-300"
            />
            <StatPill
              label={levelLabel}
              value={`${overview.current_level.lessons_done}/${overview.current_level.lessons_total}`}
              colorClass="from-violet-500/15 to-violet-950/35 border-violet-500/20"
              textClass="text-violet-300"
            />
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3 lg:gap-8">
        <div className="flex flex-col gap-6 lg:col-span-2">
          {/* Progress */}
          <section className="rounded-xl border border-slate-700/70 bg-slate-900/50 p-5 shadow-md">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-100">
                Progresso — {levelLabel}
              </h2>
            </div>
            <ProgressBar value={overview.current_level.progress_pct} />
            <p className="mt-3 text-sm text-slate-500">
              {overview.current_level.lessons_done} de{" "}
              {overview.current_level.lessons_total} aulas concluídas neste
              nível
            </p>
          </section>

          {/* Next lesson */}
          <section className="rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 to-slate-900/60 p-5 shadow-md">
            <h2 className="text-base font-semibold text-white">Próxima aula</h2>
            {overview.next_lesson ? (
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-slate-100">
                    {overview.next_lesson.title}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    Nível {overview.next_lesson.level_number} · ~
                    {overview.next_lesson.duration_min} min ·{" "}
                    {overview.next_lesson.xp_reward} XP
                  </p>
                </div>
                <Link
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/40 transition hover:bg-indigo-500"
                  href={`/lesson/${overview.next_lesson.id}`}
                >
                  Continuar
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </Link>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-500">
                Nenhuma aula em aberto. Conclua o diagnóstico ou acesse{" "}
                <Link
                  className="font-medium text-indigo-400 underline"
                  href="/lessons"
                >
                  todas as aulas
                </Link>
                .
              </p>
            )}
          </section>

          {/* Recent activity */}
          {overview.recent_activity && overview.recent_activity.length > 0 && (
            <section className="rounded-xl border border-slate-700/70 bg-slate-900/40 p-5">
              <h2 className="mb-4 text-base font-semibold text-slate-100">
                Atividade recente
              </h2>
              <ul className="divide-y divide-slate-800/80">
                {overview.recent_activity.map((r) => {
                  const scorePct =
                    r.score != null ? Math.round(r.score * 100) : null;
                  const status =
                    scorePct != null && scorePct >= 75
                      ? "completed"
                      : scorePct != null
                        ? "in_progress"
                        : "available";
                  return (
                    <li
                      className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                      key={r.lesson_id}
                    >
                      <span className="text-sm text-slate-300">{r.title}</span>
                      <div className="flex shrink-0 items-center gap-2">
                        {scorePct != null && (
                          <span className="text-xs tabular-nums text-slate-500">
                            {scorePct}%
                          </span>
                        )}
                        <Badge status={status} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </div>

        {/* Lesson strip */}
        <aside className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Trilha
            </h2>
            <Link
              className="text-xs font-medium text-indigo-400 hover:text-indigo-300"
              href="/lessons"
            >
              Ver tudo
            </Link>
          </div>
          <div className="flex max-h-[min(30rem,70vh)] flex-col gap-1.5 overflow-y-auto rounded-xl border border-slate-700/60 bg-slate-950/40 p-2">
            {lessons.map((l) => (
              <LessonStripItem key={l.id} lesson={l} />
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

function StatPill({
  label,
  value,
  colorClass,
  textClass,
}: {
  label: string;
  value: string;
  colorClass: string;
  textClass: string;
}) {
  return (
    <div
      className={`rounded-xl border bg-gradient-to-br px-4 py-3 shadow-inner ${colorClass}`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p className={`mt-1 text-lg font-semibold tabular-nums ${textClass}`}>
        {value}
      </p>
    </div>
  );
}

function LessonStripItem({ lesson: l }: { lesson: LessonRow }) {
  const locked = l.status === "locked";
  const done = l.status === "completed";

  const dotClass = done
    ? "bg-emerald-400"
    : locked
      ? "bg-slate-700"
      : "bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.5)]";

  const row = (
    <div className="flex items-center gap-3 rounded-lg px-2.5 py-2.5 transition hover:bg-slate-800/60">
      <span className={`h-2 w-2 shrink-0 rounded-full ${dotClass}`} />
      <div className="min-w-0 flex-1">
        <p
          className={`truncate text-sm ${locked ? "text-slate-600" : "font-medium text-slate-200"}`}
        >
          {l.title}
        </p>
        <p className="text-xs text-slate-600">
          Nv. {l.level_number} · {l.xp_reward} XP
        </p>
      </div>
      {done && (
        <svg
          className="h-3.5 w-3.5 shrink-0 text-emerald-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M5 13l4 4L19 7"
          />
        </svg>
      )}
    </div>
  );

  if (locked) return <div>{row}</div>;
  return <Link href={`/lesson/${l.id}`}>{row}</Link>;
}
