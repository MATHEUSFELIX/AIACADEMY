"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSupabase } from "@/lib/supabase";
import { apiFetch, ApiError } from "@/lib/api";

interface ProgressPayload {
  by_module: Record<string, { total: number; completed: number; avg_score: number }>;
  streak: { current: number; best: number; last_activity: string };
}

export default function ProgressPage() {
  const [data, setData] = useState<ProgressPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const supabase = getSupabase();
        const { data: sessionData } = await supabase.auth.getSession();
        const token = sessionData.session?.access_token;
        if (!token) {
          setError("Faça login.");
          return;
        }
        const json = await apiFetch<ProgressPayload>("/progress/me", token);
        if (!cancelled) {
          setData(json);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Erro ao carregar progresso.");
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
          Login
        </Link>
      </div>
    );
  }

  if (!data) {
    return <p className="text-slate-400">Carregando…</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">Progresso</h1>
      <p className="text-slate-400">
        Streak atual: {data.streak.current} dias · melhor: {data.streak.best}
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {Object.entries(data.by_module).map(([mod, v]) => (
          <div
            className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm"
            key={mod}
          >
            <p className="font-medium text-slate-200">Módulo {mod}</p>
            <p className="mt-2 text-slate-400">
              {v.completed}/{v.total} concluídas · média {v.avg_score.toFixed(2)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
