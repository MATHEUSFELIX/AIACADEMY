"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";
import { ProgressBar } from "@/components/ui/ProgressBar";

interface ProgressPayload {
  by_module: Record<
    string,
    { total: number; completed: number; avg_score: number }
  >;
  streak: { current: number; best: number; last_activity: string };
}

export default function ProgressPage() {
  const [data, setData] = useState<ProgressPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getAuthToken();
        if (!token) {
          setError("Faça login.");
          return;
        }
        const json = await apiFetch<ProgressPayload>("/progress/me", token);
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled)
          setError(
            e instanceof ApiError ? e.message : "Erro ao carregar progresso.",
          );
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
          Login
        </Link>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-6">
        <div className="h-8 w-48 animate-pulse rounded-lg bg-slate-800" />
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-xl bg-slate-800/70"
            />
          ))}
        </div>
      </div>
    );
  }

  const modules = Object.entries(data.by_module);
  const totalDone = modules.reduce((acc, [, v]) => acc + v.completed, 0);
  const totalAll = modules.reduce((acc, [, v]) => acc + v.total, 0);

  return (
    <div className="flex flex-col gap-8 animate-fade-in">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-400/80">
          Progresso
        </p>
        <h1 className="mt-1.5 text-2xl font-semibold tracking-tight">
          Seu desempenho
        </h1>
      </div>

      {/* Streak card */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StreakCard
          label="Sequência atual"
          value={data.streak.current}
          unit="dias"
          color="text-emerald-300"
          bg="from-emerald-500/10 to-emerald-950/20 border-emerald-800/40"
        />
        <StreakCard
          label="Melhor sequência"
          value={data.streak.best}
          unit="dias"
          color="text-violet-300"
          bg="from-violet-500/10 to-violet-950/20 border-violet-800/40"
        />
        <StreakCard
          label="Aulas concluídas"
          value={totalDone}
          unit={`/ ${totalAll}`}
          color="text-indigo-300"
          bg="from-indigo-500/10 to-indigo-950/20 border-indigo-800/40"
        />
      </div>

      {/* Modules */}
      {modules.length > 0 && (
        <section>
          <h2 className="mb-4 text-base font-semibold text-slate-100">
            Por módulo
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {modules.map(([mod, v]) => {
              const pct =
                v.total > 0 ? Math.round((v.completed / v.total) * 100) : 0;
              const avgPct = Math.round(v.avg_score * 100);
              return (
                <div
                  key={mod}
                  className="flex flex-col gap-4 rounded-xl border border-slate-700/70 bg-slate-900/50 p-5 shadow-md"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-slate-200">
                      Módulo {mod}
                    </p>
                    <span className="text-xs tabular-nums text-slate-500">
                      {v.completed}/{v.total} aulas
                    </span>
                  </div>

                  <ProgressBar
                    value={pct}
                    label="Conclusão"
                    size="sm"
                  />

                  {v.avg_score > 0 && (
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>Score médio</span>
                      <span
                        className={`font-semibold tabular-nums ${
                          avgPct >= 75 ? "text-emerald-400" : "text-amber-400"
                        }`}
                      >
                        {avgPct}%
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {modules.length === 0 && (
        <div className="rounded-xl border border-slate-700/60 bg-slate-900/40 px-6 py-10 text-center">
          <p className="text-slate-400">Nenhuma aula concluída ainda.</p>
          <p className="mt-2 text-sm text-slate-500">
            Comece pelo{" "}
            <Link className="text-indigo-400 underline" href="/diagnostic">
              diagnóstico
            </Link>{" "}
            para definir seu nível.
          </p>
        </div>
      )}
    </div>
  );
}

function StreakCard({
  label,
  value,
  unit,
  color,
  bg,
}: {
  label: string;
  value: number;
  unit: string;
  color: string;
  bg: string;
}) {
  return (
    <div
      className={`rounded-xl border bg-gradient-to-br p-5 shadow-md ${bg}`}
    >
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${color}`}>
        {value}
        <span className="ml-1.5 text-base font-normal text-slate-500">
          {unit}
        </span>
      </p>
    </div>
  );
}
