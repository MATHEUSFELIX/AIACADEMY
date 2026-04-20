import Link from "next/link";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen app-shell">
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Link className="text-sm font-semibold tracking-tight text-white sm:text-base" href="/dashboard">
            MasterAI Academy
          </Link>
          <nav className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1 text-xs font-medium text-slate-400 sm:gap-x-6 sm:text-sm">
            <Link className="transition hover:text-indigo-300" href="/dashboard">
              Painel
            </Link>
            <Link className="transition hover:text-indigo-300" href="/lessons">
              Aulas
            </Link>
            <Link className="transition hover:text-indigo-300" href="/diagnostic">
              Diagnóstico
            </Link>
            <Link className="transition hover:text-indigo-300" href="/progress">
              Progresso
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
