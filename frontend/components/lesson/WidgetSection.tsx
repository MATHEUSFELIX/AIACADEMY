"use client";

import { useState } from "react";

interface Control {
  id: string;
  label: string;
  min: number;
  max: number;
  default: number;
  unit?: string;
}

interface WidgetConfig {
  type?: string;
  controls?: Control[];
  chart_type?: string;
  reveal_button?: { label?: string; insight_template?: string };
}

function interpolate(template: string, values: Record<string, number | string>) {
  return template.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ""));
}

function LineChart({ data, height = 100 }: { data: number[]; height?: number }) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const pad = { top: 8, bottom: 8, left: 2, right: 2 };
  const w = 100;
  const innerH = height - pad.top - pad.bottom;

  const pts = data.map((v, i) => {
    const x = pad.left + (i / (data.length - 1)) * (w - pad.left - pad.right);
    const y = pad.top + innerH - ((v - min) / range) * innerH;
    return [x, y] as [number, number];
  });

  const line = pts.map((p) => p.join(",")).join(" ");
  const area = `${pts[0][0]},${height - pad.bottom} ${line} ${pts[pts.length - 1][0]},${height - pad.bottom}`;

  return (
    <svg
      viewBox={`0 0 ${w} ${height}`}
      className="w-full"
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id="wg-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgb(99 102 241)" stopOpacity="0.4" />
          <stop offset="100%" stopColor="rgb(99 102 241)" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={area} fill="url(#wg-grad)" />
      <polyline
        points={line}
        fill="none"
        stroke="rgb(129 140 248)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx={pts[pts.length - 1][0]}
        cy={pts[pts.length - 1][1]}
        r="2.5"
        fill="rgb(165 180 252)"
      />
    </svg>
  );
}

function BarChart({ data, height = 100 }: { data: number[]; height?: number }) {
  const max = Math.max(...data, 1);
  const n = data.length;
  const pad = 6;
  const barW = (100 - pad * 2) / n - 2;

  return (
    <svg viewBox={`0 0 100 ${height}`} className="w-full" preserveAspectRatio="none">
      {data.map((v, i) => {
        const barH = (v / max) * (height - 12);
        const x = pad + i * ((100 - pad * 2) / n) + 1;
        const y = height - barH - 8;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barW}
            height={barH}
            rx="2"
            fill="rgb(99 102 241)"
            fillOpacity={0.5 + (i / n) * 0.5}
          />
        );
      })}
    </svg>
  );
}

export function WidgetSection({
  config,
  onContinue,
}: {
  config: Record<string, unknown>;
  onContinue: () => void;
}) {
  const wc = config as unknown as WidgetConfig;
  const controls = wc.controls ?? [];
  const chartType = wc.chart_type ?? "line";
  const reveal = wc.reveal_button;

  const [values, setValues] = useState<Record<string, number>>(
    Object.fromEntries(controls.map((c) => [c.id, c.default])),
  );
  const [revealed, setRevealed] = useState(false);

  const primaryCtrl = controls[0];

  const chartData = (() => {
    if (controls.length === 0) {
      return [40, 55, 48, 62, 70, 65, 78, 85, 80, 92];
    }
    const lift = primaryCtrl
      ? values[primaryCtrl.id] / primaryCtrl.max
      : 0.5;
    return Array.from({ length: 10 }, (_, i) => {
      const base = (i / 9) * 60 + 20;
      const boost = i > 4 ? (i - 4) * lift * 12 : 0;
      return Math.min(100, base + boost);
    });
  })();

  const insight =
    reveal?.insight_template ? interpolate(reveal.insight_template, values) : null;

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 animate-fade-in">
      <div className="p-6 sm:p-8">
        <h2 className="text-base font-semibold text-slate-100">
          Widget interativo
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {controls.length > 0
            ? "Ajuste os controles e observe o impacto no gráfico."
            : "Visualização do resultado esperado."}
        </p>

        <div className={`mt-6 grid gap-6 ${controls.length > 0 ? "sm:grid-cols-[1fr_2fr]" : ""}`}>
          {controls.length > 0 && (
            <div className="flex flex-col gap-6">
              {controls.map((ctrl) => (
                <div key={ctrl.id} className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-slate-300">
                      {ctrl.label}
                    </label>
                    <span className="rounded-md bg-indigo-600/20 px-2.5 py-0.5 text-sm font-semibold tabular-nums text-indigo-300">
                      {values[ctrl.id]}
                      {ctrl.unit ?? ""}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={ctrl.min}
                    max={ctrl.max}
                    value={values[ctrl.id]}
                    onChange={(e) => {
                      setValues((v) => ({
                        ...v,
                        [ctrl.id]: Number(e.target.value),
                      }));
                      setRevealed(false);
                    }}
                    className="h-1.5 w-full cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-slate-600">
                    <span>
                      {ctrl.min}
                      {ctrl.unit ?? ""}
                    </span>
                    <span>
                      {ctrl.max}
                      {ctrl.unit ?? ""}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-3">
            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <div className="h-[110px]">
                {chartType === "bar" ? (
                  <BarChart data={chartData} height={100} />
                ) : (
                  <LineChart data={chartData} height={100} />
                )}
              </div>
              {primaryCtrl && (
                <p className="mt-2 text-center text-[11px] text-slate-600">
                  {primaryCtrl.label} ={" "}
                  <span className="font-medium text-slate-500">
                    {values[primaryCtrl.id]}
                    {primaryCtrl.unit ?? ""}
                  </span>
                </p>
              )}
            </div>

            {reveal?.label && !revealed && (
              <button
                type="button"
                onClick={() => setRevealed(true)}
                className="w-full rounded-lg border border-indigo-500/30 bg-indigo-600/10 py-2.5 text-sm font-medium text-indigo-300 transition hover:bg-indigo-600/20"
              >
                {reveal.label}
              </button>
            )}

            {revealed && insight && (
              <div className="animate-fade-in rounded-lg border border-indigo-500/20 bg-indigo-950/30 p-4 text-sm leading-relaxed text-indigo-200">
                {insight}
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 flex justify-end border-t border-slate-800/80 pt-6">
          <button
            type="button"
            onClick={onContinue}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500"
          >
            Continuar para a KB
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
