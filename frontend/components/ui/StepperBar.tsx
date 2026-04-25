interface StepItem {
  key: string;
  label: string;
}

interface StepperBarProps {
  steps: StepItem[];
  current: string;
  unlockedMax: number;
  onChange: (key: string) => void;
}

export function StepperBar({
  steps,
  current,
  unlockedMax,
  onChange,
}: StepperBarProps) {
  const currentIdx = steps.findIndex((s) => s.key === current);

  return (
    <div className="flex items-start">
      {steps.map((step, idx) => {
        const isDone = idx < currentIdx;
        const isActive = idx === currentIdx;
        const isLocked = idx > unlockedMax;

        return (
          <div key={step.key} className="flex flex-1 items-start">
            <button
              type="button"
              disabled={isLocked}
              onClick={() => !isLocked && onChange(step.key)}
              className={`group flex flex-1 flex-col items-center gap-2 transition ${
                isLocked ? "cursor-not-allowed" : "cursor-pointer"
              }`}
            >
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ring-2 transition-all duration-300 ${
                  isActive
                    ? "bg-indigo-600 ring-indigo-400 text-white shadow-lg shadow-indigo-950/60"
                    : isDone
                      ? "bg-emerald-600/25 ring-emerald-500/60 text-emerald-400"
                      : "bg-slate-800/80 ring-slate-700/60 text-slate-600"
                }`}
              >
                {isDone ? (
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : (
                  idx + 1
                )}
              </div>
              <span
                className={`text-center text-[11px] font-medium leading-tight ${
                  isActive
                    ? "text-indigo-300"
                    : isDone
                      ? "text-emerald-500/80"
                      : "text-slate-600"
                }`}
              >
                {step.label}
              </span>
            </button>
            {idx < steps.length - 1 && (
              <div
                className={`mx-1 mt-4 h-px flex-1 transition-all duration-500 ${
                  idx < currentIdx ? "bg-emerald-600/40" : "bg-slate-800"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
