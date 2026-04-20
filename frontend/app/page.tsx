import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 px-6">
      <h1 className="text-3xl font-semibold tracking-tight">MasterAI Academy</h1>
      <p className="text-slate-400">
        Plataforma de aprendizado de IA e dados. Entre para acessar o painel, o
        diagnóstico e as aulas.
      </p>
      <div className="flex gap-4">
        <Link
          className="rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500"
          href="/login"
        >
          Entrar
        </Link>
        <Link
          className="rounded-lg border border-slate-600 px-4 py-2 font-medium text-slate-200 hover:border-slate-500"
          href="/dashboard"
        >
        Painel
        </Link>
      </div>
    </main>
  );
}
