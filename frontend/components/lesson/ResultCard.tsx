interface ResultCardProps {
  feedback: string;
  score?: number;
  xpEarned?: number;
}

export function ResultCard({ feedback, score, xpEarned }: ResultCardProps) {
  const scorePct = score != null ? Math.round(score * 100) : null;
  const passed = scorePct != null && scorePct >= 75;

  return (
    <div className="animate-fade-in rounded-xl border border-slate-700/60 bg-slate-900/60 overflow-hidden">
      {(scorePct != null || xpEarned != null) && (
        <div
          className={`flex items-center justify-between border-b px-5 py-3 ${
            passed
              ? "border-emerald-800/50 bg-emerald-950/20"
              : "border-slate-800 bg-slate-950/40"
          }`}
        >
          <div className="flex items-center gap-2">
            <div
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                passed
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-slate-700/60 text-slate-400"
              }`}
            >
              {passed ? "✓" : "·"}
            </div>
            <span
              className={`text-sm font-medium ${
                passed ? "text-emerald-300" : "text-slate-400"
              }`}
            >
              {passed ? "Exercício concluído" : "Resposta enviada"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {scorePct != null && (
              <span className="text-sm font-semibold tabular-nums text-slate-300">
                {scorePct}%
              </span>
            )}
            {xpEarned != null && (
              <span className="rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-300 ring-1 ring-amber-500/30">
                +{xpEarned} XP
              </span>
            )}
          </div>
        </div>
      )}

      <div className="p-5">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-indigo-400/70">
          Feedback — BrainAgent
        </p>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
          {feedback}
        </p>
      </div>
    </div>
  );
}
