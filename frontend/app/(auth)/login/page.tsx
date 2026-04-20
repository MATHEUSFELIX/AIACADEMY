"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { DEV_SKIP_AUTH } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (DEV_SKIP_AUTH) {
      router.replace("/dashboard");
    }
  }, [router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { getSupabase } = await import("@/lib/supabase");
      const supabase = getSupabase();
      const { error: signErr } = await supabase.auth.signInWithPassword({ email, password });
      if (signErr) {
        setError(signErr.message);
        return;
      }
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao entrar");
    } finally {
      setLoading(false);
    }
  }

  if (DEV_SKIP_AUTH) {
    return <p className="p-8 text-slate-400">Redirecionando para o painel…</p>;
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-8 px-6">
      <div>
        <h1 className="text-2xl font-semibold">Entrar</h1>
        <p className="mt-2 text-sm text-slate-400">
          Use a conta criada no Supabase (Auth).
        </p>
      </div>
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <label className="flex flex-col gap-1 text-sm">
          E-mail
          <input
            className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Senha
          <input
            className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        <button
          className="rounded-lg bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          disabled={loading}
          type="submit"
        >
          {loading ? "Entrando…" : "Continuar"}
        </button>
      </form>
      <p className="text-center text-sm text-slate-500">
        <Link href="/">← Voltar</Link>
      </p>
    </main>
  );
}
