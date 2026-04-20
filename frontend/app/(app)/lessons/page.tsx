"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";

interface LessonRow {
  id: string;
  title: string;
  module: string;
  level_number: number;
  order_in_level: number;
  xp_reward: number;
  duration_min: number;
  status: string;
  prerequisites: string[];
}

export default function LessonsCatalogPage() {
  const [lessons, setLessons] = useState<LessonRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getAuthToken();
        if (!token) {
          setError("Faça login.");
          setLoading(false);
          return;
        }
        const json = await apiFetch<{ lessons: LessonRow[] }>("/lessons", token);
        if (!cancelled) {
          setLessons(json.lessons);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Erro ao carregar aulas.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const grouped = useMemo(() => {
    const m = new Map<number, LessonRow[]>();
    for (const l of lessons) {
      const arr = m.get(l.level_number) ?? [];
      arr.push(l);
      m.set(l.level_number, arr);
    }
    return Array.from(m.entries()).sort((a, b) => a[0] - b[0]);
  }, [lessons]);

  if (error) {
    return (
      <div className="rounded-xl border border-red-900/50 bg-red-950/20 px-4 py-3 text-red-300">
        {error}{" "}
        <Link className="underline" href="/login">
          Login
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-2">
        <div className="h-8 w-48 animate-pulse rounded-lg bg-slate-800" />
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="h-28 animate-pulse rounded-xl bg-slate-800/80" />
          <div className="h-28 animate-pulse rounded-xl bg-slate-800/80" />
        </div>
      </div>
    );
  }

  if (!lessons.length) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900/50 px-5 py-8 text-center">
        <p className="text-slate-400">Nenhuma aula encontrada no catálogo.</p>
        <p className="mt-2 text-sm text-slate-500">
          Confirme se o seed foi executado no backend (<code className="rounded bg-slate-800 px-1">seed_lessons</code>
          ).
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <header className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-950/80 via-slate-900/90 to-slate-950 p-6 shadow-lg shadow-indigo-950/40">
        <p className="text-xs font-medium uppercase tracking-wider text-indigo-300/90">Catálogo</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white">Trilha de aulas</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
          Progressão por nível. Aulas bloqueadas abrem quando cumpres o exercício anterior (≥ 75%) e
          pré-requisitos.
        </p>
      </header>

      <div className="flex flex-col gap-10">
        {grouped.map(([level, items]) => (
          <section key={level}>
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-100">
              <span className="rounded-lg bg-indigo-600/30 px-2 py-0.5 text-sm font-medium text-indigo-200">
                Nível {level}
              </span>
              <span className="text-slate-500">·</span>
              <span className="text-sm font-normal text-slate-500">{items.length} aula(s)</span>
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {items.map((l) => (
                <LessonCard key={l.id} lesson={l} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function statusUi(status: string): { label: string; className: string } {
  switch (status) {
    case "completed":
      return { label: "Concluída", className: "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30" };
    case "in_progress":
      return { label: "Em progresso", className: "bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/35" };
    case "available":
      return { label: "Disponível", className: "bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-400/35" };
    default:
      return { label: "Bloqueada", className: "bg-slate-700/40 text-slate-400 ring-1 ring-slate-600/50" };
  }
}

function LessonCard({ lesson: l }: { lesson: LessonRow }) {
  const st = statusUi(l.status);
  const open = l.status !== "locked";

  const inner = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium leading-snug text-slate-100">{l.title}</p>
          <p className="mt-1 text-xs text-slate-500">
            Módulo {l.module} · ~{l.duration_min} min · {l.xp_reward} XP
          </p>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${st.className}`}>
          {st.label}
        </span>
      </div>
      {!open && l.prerequisites.length > 0 ? (
        <p className="mt-3 border-t border-slate-700/60 pt-3 text-xs text-slate-500">
          Requer: {l.prerequisites.join(", ")}
        </p>
      ) : null}
    </>
  );

  if (open) {
    return (
      <Link
        className="group block rounded-xl border border-slate-700/80 bg-gradient-to-br from-slate-900/90 to-slate-950 p-5 shadow-md transition hover:border-indigo-500/50 hover:shadow-indigo-950/30"
        href={`/lesson/${l.id}`}
      >
        {inner}
        <p className="mt-4 text-xs font-medium text-indigo-400 opacity-80 transition group-hover:opacity-100">
          Abrir aula →
        </p>
      </Link>
    );
  }

  return (
    <div className="rounded-xl border border-slate-800/90 bg-slate-950/50 p-5 opacity-85">{inner}</div>
  );
}
