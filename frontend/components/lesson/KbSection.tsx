"use client";

import { useState } from "react";

interface KbContent {
  resumo?: string;
  quando_usar?: string[];
  quando_nao_usar?: string[];
  formula?: Record<string, unknown>;
  codigo?: string;
  antipatterns?: string[];
  fintech_aplicacao?: string;
}

type KbTab = "resumo" | "quando" | "codigo" | "antipatterns";

const TABS: { key: KbTab; label: string }[] = [
  { key: "resumo", label: "Resumo" },
  { key: "quando", label: "Quando usar" },
  { key: "codigo", label: "Código" },
  { key: "antipatterns", label: "Antipatterns" },
];

export function KbSection({
  content,
  onContinue,
}: {
  content: Record<string, unknown>;
  onContinue: () => void;
}) {
  const kb = content as unknown as KbContent;
  const [activeTab, setActiveTab] = useState<KbTab>("resumo");

  const tabHasContent = (key: KbTab) => {
    if (key === "resumo") return !!kb.resumo;
    if (key === "quando")
      return !!(kb.quando_usar?.length || kb.quando_nao_usar?.length);
    if (key === "codigo") return !!kb.codigo;
    if (key === "antipatterns") return !!kb.antipatterns?.length;
    return false;
  };

  const visibleTabs = TABS.filter((t) => tabHasContent(t.key));

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 animate-fade-in">
      <div className="p-6 sm:p-8">
        <h2 className="text-base font-semibold text-slate-100">
          Base de conhecimento
        </h2>

        {visibleTabs.length > 0 && (
          <div className="mt-4 flex gap-1 rounded-xl bg-slate-950/60 p-1">
            {visibleTabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 rounded-lg py-2 text-xs font-medium transition ${
                  activeTab === tab.key
                    ? "bg-slate-800 text-slate-100 shadow-sm"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}

        <div className="mt-5 min-h-[140px] animate-fade-in" key={activeTab}>
          {activeTab === "resumo" && (
            <div className="flex flex-col gap-4">
              {kb.resumo && (
                <p className="leading-relaxed text-slate-200">{kb.resumo}</p>
              )}
              {kb.fintech_aplicacao && (
                <div className="rounded-lg border border-indigo-500/20 bg-indigo-950/20 p-4">
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-400/80">
                    Aplicação Fintech
                  </p>
                  <p className="text-sm leading-relaxed text-indigo-200">
                    {kb.fintech_aplicacao}
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === "quando" && (
            <div className="grid gap-5 sm:grid-cols-2">
              {kb.quando_usar?.length ? (
                <div>
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-emerald-400/80">
                    ✓ Quando usar
                  </p>
                  <ul className="space-y-2.5">
                    {kb.quando_usar.map((item, i) => (
                      <li key={i} className="flex gap-2.5 text-sm text-slate-300">
                        <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] text-emerald-400">
                          ✓
                        </span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {kb.quando_nao_usar?.length ? (
                <div>
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-red-400/80">
                    ✗ Quando não usar
                  </p>
                  <ul className="space-y-2.5">
                    {kb.quando_nao_usar.map((item, i) => (
                      <li key={i} className="flex gap-2.5 text-sm text-slate-300">
                        <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-red-500/20 text-[10px] text-red-400">
                          ✗
                        </span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          )}

          {activeTab === "codigo" && kb.codigo && (
            <div className="relative">
              <div className="absolute right-3 top-3">
                <span className="rounded-md bg-slate-800 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
                  SQL
                </span>
              </div>
              <pre className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 p-5 text-xs leading-relaxed text-slate-300">
                <code>{kb.codigo}</code>
              </pre>
            </div>
          )}

          {activeTab === "antipatterns" && kb.antipatterns?.length && (
            <ul className="space-y-3">
              {kb.antipatterns.map((ap, i) => (
                <li
                  key={i}
                  className="flex gap-3 rounded-lg border border-red-900/30 bg-red-950/15 p-3.5"
                >
                  <span className="shrink-0 text-red-400">⚠</span>
                  <span className="text-sm text-slate-300">{ap}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="mt-8 flex justify-end border-t border-slate-800/80 pt-6">
          <button
            type="button"
            onClick={onContinue}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500"
          >
            Ir para o exercício
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </section>
  );
}
