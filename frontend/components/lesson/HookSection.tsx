"use client";

import { useEffect, useState } from "react";

interface HookConfig {
  icon_sequence?: string[];
  scenes?: { text?: string; sub?: string }[];
  cta?: string;
}

function DashboardIcon() {
  return (
    <svg className="h-14 w-14" viewBox="0 0 56 56" fill="none">
      <rect
        x="4" y="4" width="22" height="24" rx="4"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.12"
        className="animate-fade-in"
      />
      <rect
        x="30" y="4" width="22" height="11" rx="4"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.12"
        style={{ animationDelay: "100ms" }}
        className="animate-fade-in"
      />
      <rect
        x="30" y="19" width="22" height="9" rx="4"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.12"
        style={{ animationDelay: "200ms" }}
        className="animate-fade-in"
      />
      <rect
        x="4" y="32" width="48" height="20" rx="4"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.12"
        style={{ animationDelay: "300ms" }}
        className="animate-fade-in"
      />
      <path
        d="M10 44 L17 38 L23 41 L30 34 L37 37 L44 30"
        stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round"
        fill="none"
        style={{ animationDelay: "500ms" }}
        className="animate-fade-in"
      />
    </svg>
  );
}

function QuestionIcon() {
  return (
    <svg className="h-14 w-14" viewBox="0 0 56 56" fill="none">
      <circle
        cx="28" cy="28" r="22"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.08"
        className="animate-scale-in"
      />
      <text
        x="28" y="38"
        textAnchor="middle"
        fontSize="26"
        fontWeight="700"
        fill="currentColor"
        className="animate-fade-in"
        style={{ animationDelay: "200ms" }}
      >
        ?
      </text>
    </svg>
  );
}

function DataIcon() {
  return (
    <svg className="h-14 w-14" viewBox="0 0 56 56" fill="none">
      <ellipse
        cx="28" cy="14" rx="18" ry="7"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.12"
        className="animate-scale-in"
      />
      <path
        d="M10 14 C10 14 10 28 28 28 C46 28 46 42 46 42"
        stroke="currentColor" strokeWidth="2"
        strokeDasharray="48" strokeDashoffset="48"
        fill="none"
      >
        <animate
          attributeName="strokeDashoffset"
          from="48" to="0"
          dur="0.6s" begin="0.3s"
          fill="freeze"
        />
      </path>
      <ellipse
        cx="28" cy="42" rx="18" ry="7"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.12"
        className="animate-fade-in"
        style={{ animationDelay: "700ms" }}
      />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg className="h-14 w-14" viewBox="0 0 56 56" fill="none">
      <path
        d="M20 18 L7 28 L20 38"
        stroke="currentColor" strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round"
        strokeDasharray="44" strokeDashoffset="44"
      >
        <animate attributeName="strokeDashoffset" from="44" to="0" dur="0.4s" fill="freeze" />
      </path>
      <path
        d="M36 18 L49 28 L36 38"
        stroke="currentColor" strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round"
        strokeDasharray="44" strokeDashoffset="44"
      >
        <animate attributeName="strokeDashoffset" from="44" to="0" dur="0.4s" begin="0.2s" fill="freeze" />
      </path>
      <path
        d="M32 13 L24 43"
        stroke="currentColor" strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray="32" strokeDashoffset="32"
      >
        <animate attributeName="strokeDashoffset" from="32" to="0" dur="0.4s" begin="0.4s" fill="freeze" />
      </path>
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg className="h-14 w-14" viewBox="0 0 56 56" fill="none">
      <line x1="6" y1="44" x2="50" y2="44" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.3" />
      <path
        d="M8 40 L16 28 L24 33 L34 18 L44 22 L50 16"
        stroke="currentColor" strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round"
        strokeDasharray="72" strokeDashoffset="72"
        fill="none"
      >
        <animate attributeName="strokeDashoffset" from="72" to="0" dur="0.9s" fill="freeze" />
      </path>
      <circle cx="50" cy="16" r="3" fill="currentColor" className="animate-fade-in" style={{ animationDelay: "700ms" }} />
    </svg>
  );
}

function BrainIcon() {
  return (
    <svg className="h-14 w-14" viewBox="0 0 56 56" fill="none">
      <path
        d="M28 8 C18 8 10 15 10 24 C10 30 13 35 18 38 L18 46 L38 46 L38 38 C43 35 46 30 46 24 C46 15 38 8 28 8Z"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.1"
        className="animate-scale-in"
      />
      <path
        d="M22 22 Q28 18 34 22 M22 30 Q28 34 34 30"
        stroke="currentColor" strokeWidth="1.5"
        strokeLinecap="round" fill="none"
        className="animate-fade-in"
        style={{ animationDelay: "300ms" }}
      />
    </svg>
  );
}

function DefaultIcon() {
  return (
    <svg className="h-14 w-14" viewBox="0 0 56 56" fill="none">
      <circle
        cx="28" cy="28" r="20"
        stroke="currentColor" strokeWidth="2"
        fill="currentColor" fillOpacity="0.08"
        className="animate-scale-in"
      />
      <circle cx="28" cy="28" r="4" fill="currentColor" className="animate-fade-in" style={{ animationDelay: "300ms" }} />
    </svg>
  );
}

const ICON_MAP: Record<string, React.ReactNode> = {
  dashboard: <DashboardIcon />,
  question: <QuestionIcon />,
  data: <DataIcon />,
  code: <CodeIcon />,
  chart: <ChartIcon />,
  brain: <BrainIcon />,
};

export function HookSection({
  config,
  onContinue,
}: {
  config: Record<string, unknown>;
  onContinue: () => void;
}) {
  const hookConfig = config as unknown as HookConfig;
  const scenes = hookConfig.scenes ?? [];
  const iconSequence = hookConfig.icon_sequence ?? [];
  const cta = hookConfig.cta ?? "Continuar";

  const [currentScene, setCurrentScene] = useState(0);
  const [textVisible, setTextVisible] = useState(false);
  const [iconKey, setIconKey] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setTextVisible(true), 250);
    return () => clearTimeout(t);
  }, [currentScene]);

  function nextScene() {
    if (currentScene < scenes.length - 1) {
      setTextVisible(false);
      setTimeout(() => {
        setIconKey((k) => k + 1);
        setCurrentScene((c) => c + 1);
      }, 200);
    } else {
      onContinue();
    }
  }

  const scene = scenes[currentScene];
  const iconName = iconSequence[currentScene] ?? iconSequence[0];
  const icon = iconName && ICON_MAP[iconName] ? ICON_MAP[iconName] : <DefaultIcon />;
  const isLast = currentScene >= scenes.length - 1;

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 animate-fade-in">
      {scenes.length > 1 && (
        <div className="flex gap-1 p-5 pb-0">
          {scenes.map((_, i) => (
            <div
              key={i}
              className={`h-0.5 flex-1 rounded-full transition-all duration-500 ${
                i <= currentScene ? "bg-indigo-500" : "bg-slate-800"
              }`}
            />
          ))}
        </div>
      )}

      <div className="flex flex-col items-center px-8 py-12 text-center sm:px-14">
        <div
          key={`icon-${iconKey}`}
          className="mb-8 text-indigo-400 animate-scale-in"
        >
          {icon}
        </div>

        <div
          className={`max-w-xl transition-all duration-300 ${
            textVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
          }`}
        >
          {scene?.sub && (
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400/70">
              {scene.sub}
            </p>
          )}
          {scene?.text && (
            <p className="text-xl leading-relaxed text-slate-100 sm:text-2xl">
              {scene.text}
            </p>
          )}
        </div>

        <div className="mt-12 flex w-full items-center justify-between">
          <span className="text-xs text-slate-700">
            {scenes.length > 1 ? `${currentScene + 1} / ${scenes.length}` : ""}
          </span>
          <button
            type="button"
            onClick={nextScene}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500"
          >
            {isLast ? cta : "Próximo"}
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
