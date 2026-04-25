import { type HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "highlight" | "locked" | "success";
}

const variantClasses: Record<NonNullable<CardProps["variant"]>, string> = {
  default: "border-slate-700/70 bg-slate-900/50",
  highlight:
    "border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 to-slate-900/60",
  locked: "border-slate-800/90 bg-slate-950/50 opacity-75",
  success: "border-emerald-800/60 bg-emerald-950/20",
};

export function Card({ variant = "default", className = "", ...props }: CardProps) {
  return (
    <div
      className={`rounded-xl border p-5 shadow-md ${variantClasses[variant]} ${className}`}
      {...props}
    />
  );
}
