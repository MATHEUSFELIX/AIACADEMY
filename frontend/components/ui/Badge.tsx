interface BadgeProps {
  status: "completed" | "in_progress" | "available" | "locked";
  className?: string;
}

const statusConfig: Record<
  BadgeProps["status"],
  { label: string; className: string }
> = {
  completed: {
    label: "Concluída",
    className: "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30",
  },
  in_progress: {
    label: "Em progresso",
    className: "bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/35",
  },
  available: {
    label: "Disponível",
    className: "bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-400/35",
  },
  locked: {
    label: "Bloqueada",
    className: "bg-slate-700/40 text-slate-400 ring-1 ring-slate-600/50",
  },
};

export function Badge({ status, className = "" }: BadgeProps) {
  const cfg = statusConfig[status] ?? statusConfig.locked;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${cfg.className} ${className}`}
    >
      {cfg.label}
    </span>
  );
}
