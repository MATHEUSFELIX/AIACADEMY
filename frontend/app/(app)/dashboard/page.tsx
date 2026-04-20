"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";

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
}

export default function DashboardPage() {
  const [data, setData] = useState<Overview | null>(null);
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
        const json = await apiFetch<Overview>("/students/me/overview", token);
        if (!cancelled) {
          setData(json);
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
      <div>
        <p className="text-red-400">{error}</p>
        <Link className="mt-4 inline-block text-indigo-400" href="/login">
          Ir para login
        </Link>
      </div>
    );
  }

  if (!data) {
    return <p className="text-slate-400">Carregando…</p>;
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold">Painel</h1>
        <p className="mt-2 text-slate-400">{data.brainagent_message}</p>
      </div>
      <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="text-lg font-medium">Nível atual</h2>
        <p className="mt-2 text-slate-400">
          {data.current_level.level.replace("level_", "Nível ")}{" "}
          — {data.current_level.lessons_done}/{data.current_level.lessons_total} aulas (
          {data.current_level.progress_pct}%)
        </p>
      </section>
      <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="text-lg font-medium">Próxima aula</h2>
        {data.next_lesson ? (
          <div className="mt-4 flex flex-col gap-2">
            <p className="font-medium text-slate-100">{data.next_lesson.title}</p>
            <p className="text-sm text-slate-500">
              ~{data.next_lesson.duration_min} min · {data.next_lesson.xp_reward} XP
            </p>
            <Link
              className="mt-2 inline-flex w-fit rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
              href={`/lesson/${data.next_lesson.id}`}
            >
              Abrir aula
            </Link>
          </div>
        ) : (
          <p className="mt-2 text-slate-500">Nenhuma aula disponível no momento.</p>
        )}
      </section>
    </div>
  );
}
