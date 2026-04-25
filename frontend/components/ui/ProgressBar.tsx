interface ProgressBarProps {
  value: number;
  label?: string;
  showPercent?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export function ProgressBar({
  value,
  label,
  showPercent = true,
  size = "md",
  className = "",
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, Math.round(value)));
  const height = size === "sm" ? "h-1.5" : "h-2.5";

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {(label || showPercent) && (
        <div className="flex items-center justify-between">
          {label && <span className="text-sm text-slate-400">{label}</span>}
          {showPercent && (
            <span className="text-xs font-semibold tabular-nums text-slate-400">
              {pct}%
            </span>
          )}
        </div>
      )}
      <div className={`overflow-hidden rounded-full bg-slate-800 ${height}`}>
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-[width] duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
