"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";
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
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Falha ao carregar painel.");
        }
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
      <div className="flex flex-col gap-4">
        <div className="h-10 w-56 animate-pulse rounded-lg bg-slate-800" />
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="h-28 animate-pulse rounded-xl bg-slate-800/90 lg:col-span-2" />
          <div className="h-28 animate-pulse rounded-xl bg-slate-800/70" />
        </div>
        <div className="h-48 animate-pulse rounded-xl bg-slate-800/70" />
      </div>
    );
  }

  const levelLabel = overview.current_level.level.replace("level_", "Nível ");

  return (
    <div className="flex flex-col gap-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl border border-indigo-500/25 bg-gradient-to-br from-indigo-950/90 via-slate-900 to-slate-950 p-6 shadow-xl shadow-indigo-950/50 sm:p-8">
        <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-indigo-600/15 blur-3xl" />
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-300/90">Painel</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
              Olá{me.name ? `, ${me.name.split(" ")[0]}` : ""}
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-400">{overview.brainagent_message}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <StatPill label="XP total" value={me.total_xp ?? 0} accent="from-amber-500/20 to-amber-950/40" />
            <StatPill label="Sequência" value={`${me.streak_days ?? 0} dias`} accent="from-emerald-500/15 to-emerald-950/30" />
            <StatPill label={levelLabel} value={`${overview.current_level.lessons_done}/${overview.current_level.lessons_total}`} accent="from-violet-500/15 to-violet-950/35" />
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3 lg:gap-8">
        {/* Progress + next */}
        <div className="flex flex-col gap-6 lg:col-span-2">
          <section className="rounded-xl border border-slate-700/70 bg-slate-900/50 p-5 shadow-lg">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-slate-100">Progresso no nível</h2>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-medium text-slate-400">
                {overview.current_level.progress_pct}% completo
              </span>
            </div>
            <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-[width]"
                style={{ width: `${Math.min(100, overview.current_level.progress_pct)}%` }}
              />
            </div>
            <p className="mt-3 text-sm text-slate-500">
              {overview.current_level.lessons_done} de {overview.current_level.lessons_total} aulas concluídas neste nível.
            </p>
          </section>

          <section className="rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 to-slate-900/60 p-5 shadow-lg">
            <h2 className="text-base font-semibold text-white">Próxima aula</h2>
            {overview.next_lesson ? (
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-slate-100">{overview.next_lesson.title}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    Nível {overview.next_lesson.level_number} · ~{overview.next_lesson.duration_min} min ·{" "}
                    {overview.next_lesson.xp_reward} XP
                  </p>
                </div>
                <Link
                  className="inline-flex shrink-0 items-center justify-center rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/40 transition hover:bg-indigo-500"
                  href={`/lesson/${overview.next_lesson.id}`}
                >
                  Continuar
                </Link>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-500">
                Nenhuma aula em aberto. Conclui o diagnóstico ou avança na trilha em{" "}
                <Link className="font-medium text-indigo-400 underline" href="/lessons">
                  Todas as aulas
                </Link>
                .
              </p>
            )}
          </section>

          {overview.recent_activity && overview.recent_activity.length > 0 ? (
            <section className="rounded-xl border border-slate-700/70 bg-slate-900/40 p-5">
              <h2 className="text-base font-semibold text-slate-100">Atividade recente</h2>
              <ul className="mt-4 space-y-3">
                {overview.recent_activity.map((r) => (
                  <li
                    className="flex items-center justify-between gap-3 border-b border-slate-800/80 pb-3 last:border-0 last:pb-0"
                    key={r.lesson_id}
                  >
                    <span className="text-sm text-slate-300">{r.title}</span>
                    <span className="shrink-0 text-xs text-slate-500">
                      {r.score != null ? `${Math.round(r.score * 100)}%` : "—"}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        {/* Lesson strip */}
        <aside className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Trilha</h2>
            <Link className="text-xs font-medium text-indigo-400 hover:text-indigo-300" href="/lessons">
              Ver tudo
            </Link>
          </div>
          <div className="flex max-h-[min(28rem,70vh)] flex-col gap-2 overflow-y-auto rounded-xl border border-slate-700/60 bg-slate-950/40 p-3">
            {lessons.map((l) => (
              <LessonStrip key={l.id} lesson={l} />
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
  accent,
}: {
  label: string;
  value: string | number;
  accent: string;
}) {
  return (
    <div
      className={`rounded-xl border border-white/10 bg-gradient-to-br px-4 py-3 shadow-inner ${accent}`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-white">{value}</p>
    </div>
  );
}

function LessonStrip({ lesson: l }: { lesson: LessonRow }) {
  const locked = l.status === "locked";
  const done = l.status === "completed";
  const dot =
    done ? "bg-emerald-400" : locked ? "bg-slate-600" : "bg-indigo-400 shadow-[0_0_10px_rgba(129,140,248,0.6)]";

  const row = (
    <div className="flex items-center gap-3 rounded-lg px-2 py-2.5 transition hover:bg-slate-800/50">
      <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} />
      <div className="min-w-0 flex-1">
        <p className={`truncate text-sm ${locked ? "text-slate-500" : "font-medium text-slate-200"}`}>{l.title}</p>
        <p className="text-xs text-slate-600">Nv. {l.level_number} · {l.xp_reward} XP</p>
      </div>
    </div>
  );

  if (locked) {
    return <div>{row}</div>;
  }

  return <Link href={`/lesson/${l.id}`}>{row}</Link>;
}
