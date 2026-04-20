import Link from "next/link";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800 bg-slate-900/80">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link className="font-semibold text-slate-100" href="/dashboard">
            MasterAI Academy
          </Link>
          <nav className="flex gap-4 text-sm text-slate-400">
            <Link className="hover:text-slate-200" href="/dashboard">
              Painel
            </Link>
            <Link className="hover:text-slate-200" href="/diagnostic">
              Diagnóstico
            </Link>
            <Link className="hover:text-slate-200" href="/progress">
              Progresso
            </Link>
          </nav>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-6 py-10">{children}</div>
    </div>
  );
}
