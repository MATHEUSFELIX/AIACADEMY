"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import ModeSelector from "@/components/lesson/ModeSelector";
import { apiFetch, ApiError, getAuthToken } from "@/lib/api";

interface LessonDetail {
  id: string;
  title: string;
  subtitle: string | null;
  hook_config: Record<string, unknown>;
  widget_config: Record<string, unknown>;
  kb_content: Record<string, unknown>;
}

type Step = "hook" | "widget" | "kb" | "exercise";

type KbTab = "quando" | "formula" | "codigo" | "antipatterns";

interface ChatMessage {
  role: "student" | "brainagent";
  content: string;
}

interface ExerciseGenerateResponse {
  exercise_id: string;
  variant: string;
  context: string;
  question: string;
  data?: string;
}

interface ExerciseSubmitResponse {
  mode: string;
  feedback: string;
  xp_earned: number;
  mode_result?: Record<string, unknown>;
}

const STEP_ORDER: Step[] = ["hook", "widget", "kb", "exercise"];
const STEP_LABELS: Record<Step, string> = {
  hook: "Cenario",
  widget: "Explorar",
  kb: "Conceito",
  exercise: "Praticar",
};

function asString(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}

function asStringList(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((item): item is string => typeof item === "string");
}

function stepIndex(step: Step): number {
  return STEP_ORDER.indexOf(step);
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-800/90 bg-gradient-to-b from-slate-950/80 to-slate-950/60 p-6 shadow-[0_16px_60px_-35px_rgba(0,200,150,0.9)]">
      <div className="mb-6">
        <h2 className="text-xl font-semibold tracking-tight text-slate-100">{title}</h2>
        {subtitle ? <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}

function BrainAgentBadge({ mode }: { mode: string | null }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-cyan-600/45 bg-cyan-950/50 px-3 py-1 text-xs font-medium text-cyan-100 shadow-[0_0_0_1px_rgba(34,211,238,.08)]">
      <span className="h-2 w-2 rounded-full bg-cyan-400" />
      BrainAgent {mode ? `· modo ${mode}` : "· aguardando modo"}
    </div>
  );
}

function HookSection({
  title,
  config,
  onContinue,
}: {
  title: string;
  config: Record<string, unknown>;
  onContinue: () => void;
}) {
  const inputScenes = Array.isArray(config.scenes) ? config.scenes : [];
  const scenes = inputScenes
    .map((scene) => {
      if (!scene || typeof scene !== "object") return null;
      const rec = scene as Record<string, unknown>;
      return { text: asString(rec.text), sub: asString(rec.sub) };
    })
    .filter((scene): scene is { text: string; sub: string } => !!scene && !!scene.text);

  const fallbackScenes = [
    {
      sub: "PicPay · sala de resultados",
      text: "A campanha custou R$ 2.4M. Funcionou mesmo ou so pegou carona no mercado?",
    },
    {
      sub: "Diretor financeiro",
      text: "Precisamos separar efeito real da campanha do ruido de sazonalidade.",
    },
    {
      sub: "Seu desafio",
      text: "Use raciocinio causal para provar se houve ganho incremental de engajamento.",
    },
  ];

  const timeline = scenes.length > 0 ? scenes : fallbackScenes;
  const [current, setCurrent] = useState(0);
  const active = timeline[current];

  return (
    <Section title="Hook narrativo" subtitle="Contexto real antes da tecnica">
      <div className="rounded-2xl border border-slate-800/90 bg-slate-900/45 p-6 shadow-[inset_0_1px_0_rgba(148,163,184,.08)]">
        <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">{active.sub}</p>
        <p className="mt-4 text-lg font-medium leading-relaxed text-slate-100">{active.text}</p>
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setCurrent((v) => Math.max(v - 1, 0))}
          disabled={current === 0}
          className="rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800/70 disabled:opacity-40"
        >
          Voltar
        </button>
        {current < timeline.length - 1 ? (
          <button
            type="button"
            onClick={() => setCurrent((v) => Math.min(v + 1, timeline.length - 1))}
            className="rounded-lg border border-cyan-600/70 bg-cyan-600/10 px-4 py-2 text-sm font-medium text-cyan-100 transition hover:bg-cyan-600/20"
          >
            Continuar narrativa
          </button>
        ) : (
          <button
            type="button"
            onClick={onContinue}
            className="rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_25px_-12px_rgba(16,185,129,.9)] transition hover:brightness-110"
          >
            Entendi o problema · ir para o widget
          </button>
        )}
      </div>
      <p className="mt-4 text-xs uppercase tracking-[0.14em] text-slate-500">
        {title} · cena {current + 1}/{timeline.length}
      </p>
    </Section>
  );
}

function WidgetSection({ onContinue }: { onContinue: () => void }) {
  const [realEffect, setRealEffect] = useState(18);
  const [noise, setNoise] = useState(6);
  const [sample, setSample] = useState(500);
  const [revealDid, setRevealDid] = useState(false);

  const didEstimate = useMemo(() => {
    const noisePenalty = noise * (sample >= 500 ? 0.25 : 0.55);
    return Math.max(0, realEffect - noisePenalty + 1.3);
  }, [noise, realEffect, sample]);

  return (
    <Section title="Widget de simulacao DiD" subtitle="Explore variancia, amostra e efeito causal">
      <div className="grid gap-4 md:grid-cols-3">
        <label className="rounded-xl border border-slate-800/90 bg-slate-900/45 p-4 shadow-[inset_0_1px_0_rgba(148,163,184,.08)]">
          <p className="text-xs text-slate-400">Efeito real da campanha</p>
          <p className="mt-1 font-mono text-xl text-emerald-300">+{realEffect}%</p>
          <input
            type="range"
            min={0}
            max={40}
            value={realEffect}
            onChange={(e) => setRealEffect(Number(e.target.value))}
            className="mt-3 w-full accent-emerald-400"
          />
        </label>
        <label className="rounded-xl border border-slate-800/90 bg-slate-900/45 p-4 shadow-[inset_0_1px_0_rgba(148,163,184,.08)]">
          <p className="text-xs text-slate-400">Ruido de mercado</p>
          <p className="mt-1 font-mono text-xl text-amber-300">{noise} pts</p>
          <input
            type="range"
            min={0}
            max={20}
            value={noise}
            onChange={(e) => setNoise(Number(e.target.value))}
            className="mt-3 w-full accent-amber-400"
          />
        </label>
        <label className="rounded-xl border border-slate-800/90 bg-slate-900/45 p-4 shadow-[inset_0_1px_0_rgba(148,163,184,.08)]">
          <p className="text-xs text-slate-400">Tamanho da amostra</p>
          <p className="mt-1 font-mono text-xl text-cyan-300">{sample}</p>
          <input
            type="range"
            min={50}
            max={2000}
            step={50}
            value={sample}
            onChange={(e) => setSample(Number(e.target.value))}
            className="mt-3 w-full accent-cyan-400"
          />
        </label>
      </div>

      <div className="mt-5 rounded-xl border border-slate-800/90 bg-slate-900/45 p-4">
        <p className="text-sm text-slate-300">
          Estimativa visual:{" "}
          <span className="font-mono text-emerald-300">DiD ~ {didEstimate.toFixed(1)}pp</span>
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Quanto maior o ruido e menor a amostra, maior o risco de confundir correlacao com causalidade.
        </p>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => setRevealDid((v) => !v)}
          className="rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm text-slate-200 transition hover:bg-slate-800/80"
        >
          {revealDid ? "Ocultar explicacao" : "Revelar leitura do BrainAgent"}
        </button>
        <button
          type="button"
          onClick={onContinue}
          className="rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_25px_-12px_rgba(16,185,129,.9)] transition hover:brightness-110"
        >
          Continuar para KB
        </button>
      </div>

      {revealDid ? (
        <div className="mt-4 rounded-xl border border-emerald-700/40 bg-emerald-950/20 p-4 text-sm leading-relaxed text-emerald-100">
          BrainAgent: para defender causalidade, voce precisa mostrar tendencia pre semelhante e quantificar o
          contrafactual. O widget ja te deu a intuicao; agora vamos para a formalizacao.
        </div>
      ) : null}
    </Section>
  );
}

function KbSection({ content, onContinue }: { content: Record<string, unknown>; onContinue: () => void }) {
  const [tab, setTab] = useState<KbTab>("quando");

  const formula = asString((content.formula as Record<string, unknown> | undefined)?.did, "");
  const sqlExample = asString(
    (content.example_sql as Record<string, unknown> | undefined)?.query,
    `WITH deltas AS (
  SELECT grupo,
    AVG(CASE WHEN periodo='post' THEN engajamento END) -
    AVG(CASE WHEN periodo='pre' THEN engajamento END) AS delta
  FROM silver.campanha
  GROUP BY grupo
)
SELECT
  MAX(CASE WHEN grupo='tratado' THEN delta END) -
  MAX(CASE WHEN grupo='controle' THEN delta END) AS did_estimate
FROM deltas;`,
  );
  const antiPatterns = asStringList(content.antipatterns);

  return (
    <Section title="Knowledge Base guiada" subtitle="Regras praticas para nao errar em inferencia causal">
      <div className="mb-4 flex flex-wrap gap-2">
        {(["quando", "formula", "codigo", "antipatterns"] as KbTab[]).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setTab(option)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
              tab === option
                ? "bg-cyan-600/20 text-cyan-200 ring-1 ring-cyan-500/50"
                : "bg-slate-900 text-slate-300 ring-1 ring-slate-700 hover:bg-slate-800"
            }`}
          >
            {option}
          </button>
        ))}
      </div>

      {tab === "quando" ? (
        <div className="space-y-2 text-sm text-slate-300">
          <p>Use DiD quando houver antes/depois e grupo tratado/controle comparavel.</p>
          <p>Evite usar se a tendencia pre ja era divergente entre os grupos.</p>
        </div>
      ) : null}
      {tab === "formula" ? (
        <p className="rounded-xl border border-slate-800/90 bg-slate-900/45 p-4 font-mono text-sm text-slate-200">
          {formula || "DiD = (tratado_pos - tratado_pre) - (controle_pos - controle_pre)"}
        </p>
      ) : null}
      {tab === "codigo" ? (
        <pre className="overflow-x-auto rounded-xl border border-slate-800/90 bg-slate-900/45 p-4 text-xs text-slate-200">
          {sqlExample}
        </pre>
      ) : null}
      {tab === "antipatterns" ? (
        <ul className="space-y-2 text-sm text-slate-300">
          {(antiPatterns.length > 0 ? antiPatterns : [
            "Nao reportar DiD sem validar tendencias pre.",
            "Nao confundir ganho absoluto com efeito causal.",
            "Nao ignorar heterogeneidade por segmento de cliente.",
          ]).map((item) => (
            <li key={item} className="rounded-lg border border-rose-700/30 bg-rose-950/10 px-3 py-2">
              {item}
            </li>
          ))}
        </ul>
      ) : null}

      <button
        type="button"
        onClick={onContinue}
        className="mt-5 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_25px_-12px_rgba(16,185,129,.9)] transition hover:brightness-110"
      >
        Partir para o exercicio
      </button>
    </Section>
  );
}

function ModeSpecificResult({ mode, result }: { mode: string; result: Record<string, unknown> }) {
  if (mode === "competitive") {
    return (
      <div className="space-y-1">
        <p>Winner: {asString(result.winner, "-")}</p>
        <p>Student score: {String(result.student_score ?? "-")}</p>
        <p>Agent score: {String(result.agent_score ?? "-")}</p>
      </div>
    );
  }
  if (mode === "socratic") {
    return <p>{asString(result.next_question, "Boa resposta. Conceito consolidado pelo BrainAgent.")}</p>;
  }
  if (mode === "streaming") {
    return <p>{asString(result.streaming_thoughts, "Streaming de raciocinio registrado.")}</p>;
  }
  if (mode === "inner_monologue") {
    return <p>Hints usados: {String(result.hints_used ?? 0)} · {asString(result.independence_level, "foco em autonomia")}</p>;
  }
  if (mode === "progressive") {
    const unlocks = Array.isArray(result.next_unlocked_modes)
      ? result.next_unlocked_modes.map((item) => String(item)).join(", ")
      : "nenhum";
    return <p>Proximos modos desbloqueados: {unlocks}</p>;
  }
  return <p>Modo moment_gated: feedback orientado por momento de ajuda e independencia.</p>;
}

function ExerciseSection({ lessonId, lessonTitle }: { lessonId: string; lessonTitle: string }) {
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [selectedMode, setSelectedMode] = useState<string | null>(null);
  const [exercise, setExercise] = useState<ExerciseGenerateResponse | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [xpEarned, setXpEarned] = useState<number | null>(null);
  const [modeResult, setModeResult] = useState<Record<string, unknown> | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "brainagent",
      content:
        "Sou o BrainAgent. Escolha um modo, gere o exercicio e me pergunte qualquer coisa durante a resolucao.",
    },
  ]);

  const flowStatus = {
    modeChosen: !!selectedMode,
    exerciseGenerated: !!exercise,
    submitted: !!modeResult,
  };

  async function generateExercise() {
    if (!selectedMode) {
      setFeedback("Escolha um modo antes de gerar o exercicio.");
      return;
    }
    setLoading(true);
    setFeedback(null);
    setModeResult(null);
    setXpEarned(null);
    try {
      const token = await getAuthToken();
      if (!token) {
        setFeedback("Sessao expirada. Faça login novamente.");
        return;
      }
      const generated = await apiFetch<ExerciseGenerateResponse>(`/lessons/${lessonId}/exercise/generate`, token, {
        method: "POST",
        body: JSON.stringify({ brainagent_mode: selectedMode }),
      });
      setExercise(generated);
      setAnswer("");
      setChatMessages((prev) => [
        ...prev,
        {
          role: "brainagent",
          content: `Exercicio gerado no modo ${selectedMode}. Foque em clareza de raciocinio e impacto de negocio.`,
        },
      ]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Falha ao gerar exercicio.");
    } finally {
      setLoading(false);
    }
  }

  async function submitAnswer() {
    if (!exercise?.exercise_id || !selectedMode) return;
    if (!answer.trim()) {
      setFeedback("Escreva uma resposta antes de enviar.");
      return;
    }
    setLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) {
        setFeedback("Sessao expirada. Faça login novamente.");
        return;
      }
      const submitted = await apiFetch<ExerciseSubmitResponse>(`/lessons/${lessonId}/exercise/submit`, token, {
        method: "POST",
        body: JSON.stringify({
          exercise_id: exercise.exercise_id,
          answer,
          used_hint: false,
          brainagent_mode: selectedMode,
        }),
      });
      setFeedback(submitted.feedback);
      setModeResult(submitted.mode_result ?? null);
      setXpEarned(submitted.xp_earned);
      setChatMessages((prev) => [
        ...prev,
        {
          role: "brainagent",
          content: `Resultado processado no modo ${selectedMode}. XP ganho: ${submitted.xp_earned}.`,
        },
      ]);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Falha ao enviar resposta.");
    } finally {
      setLoading(false);
    }
  }

  async function sendChatMessage() {
    if (!chatInput.trim()) return;
    const message = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "student", content: message }]);
    setChatLoading(true);
    try {
      const token = await getAuthToken();
      if (!token) {
        setChatMessages((prev) => [
          ...prev,
          { role: "brainagent", content: "Sua sessao expirou. Faça login novamente para continuar o chat." },
        ]);
        return;
      }
      const res = await apiFetch<{ response: string }>("/brainagent/chat", token, {
        method: "POST",
        body: JSON.stringify({
          message,
          context_lesson_id: lessonId,
        }),
      });
      setChatMessages((prev) => [...prev, { role: "brainagent", content: res.response }]);
    } catch (error) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "brainagent",
          content: error instanceof Error ? error.message : "Nao consegui responder agora. Tente novamente.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  return (
    <Section title="Studio BrainAgent" subtitle="Fluxo completo: modo → geracao → envio → resultado">
      <div className="mb-5 flex flex-wrap gap-2">
        <BrainAgentBadge mode={selectedMode} />
        {[
          { id: "1", label: "Modo", done: flowStatus.modeChosen },
          { id: "2", label: "Geracao", done: flowStatus.exerciseGenerated },
          { id: "3", label: "Envio", done: flowStatus.submitted },
          { id: "4", label: "Resultado", done: flowStatus.submitted },
        ].map((item) => (
          <span
            key={item.id}
            className={`rounded-full px-3 py-1 text-xs ${
              item.done
                ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/40"
                : "bg-slate-900 text-slate-400 ring-1 ring-slate-700"
            }`}
          >
            {item.id}. {item.label}
          </span>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="space-y-5">
          {!selectedMode ? (
            <ModeSelector lessonId={lessonId} studentId="" onModeSelected={(mode) => setSelectedMode(mode)} isLoading={loading} />
          ) : (
            <div className="rounded-xl border border-slate-800/90 bg-slate-900/45 p-4">
              <p className="text-sm text-slate-300">
                Modo selecionado: <span className="font-semibold text-cyan-300">{selectedMode}</span>
              </p>
              <button
                type="button"
                onClick={() => {
                  setSelectedMode(null);
                  setExercise(null);
                  setModeResult(null);
                  setFeedback(null);
                }}
                className="mt-2 text-xs text-slate-400 underline"
              >
                Trocar modo
              </button>
            </div>
          )}

          {!exercise ? (
            <button
              type="button"
              disabled={loading || !selectedMode}
              onClick={generateExercise}
              className="rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_25px_-12px_rgba(16,185,129,.9)] transition hover:brightness-110 disabled:opacity-50"
            >
              {loading ? "Gerando..." : "Gerar exercicio com BrainAgent"}
            </button>
          ) : (
            <div className="space-y-4 rounded-xl border border-slate-800/90 bg-slate-900/45 p-5 shadow-[inset_0_1px_0_rgba(148,163,184,.08)]">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                {lessonTitle} · variant {exercise.variant}
              </p>
              {exercise.context ? <p className="text-sm text-slate-400">{exercise.context}</p> : null}
              <p className="text-base font-medium leading-relaxed text-slate-100">{exercise.question}</p>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Escreva seu raciocinio, calculo e interpretacao de negocio..."
                className="min-h-[160px] w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition ring-cyan-500/40 focus:border-cyan-600/70 focus:ring-2"
              />
              <button
                type="button"
                onClick={submitAnswer}
                disabled={loading || !answer.trim()}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
              >
                {loading ? "Avaliando..." : "Submeter resposta"}
              </button>
            </div>
          )}

          {feedback ? (
            <div className="rounded-xl border border-slate-700/90 bg-slate-950/95 p-4 shadow-[inset_0_1px_0_rgba(148,163,184,.08)]">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Feedback do BrainAgent</p>
              <p className="mt-3 whitespace-pre-wrap text-sm text-slate-200">{feedback}</p>
              {xpEarned !== null ? <p className="mt-3 text-sm text-emerald-300">XP ganho: +{xpEarned}</p> : null}
              {selectedMode && modeResult ? (
                <div className="mt-4 rounded-lg border border-cyan-700/40 bg-cyan-950/20 p-3 text-sm text-cyan-100">
                  <p className="mb-2 text-xs uppercase tracking-[0.2em] text-cyan-300">
                    Resultado especifico · {selectedMode}
                  </p>
                  <ModeSpecificResult mode={selectedMode} result={modeResult} />
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <aside className="space-y-4">
          <div className="rounded-xl border border-slate-800/90 bg-slate-900/45 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Copilot didatico</p>
            <p className="mt-2 text-sm text-slate-300">
              Use o chat para pedir pista conceitual, revisar suposicoes e validar interpretacao de negocio.
            </p>
          </div>

          <div className="flex h-[360px] flex-col rounded-xl border border-slate-800/90 bg-slate-900/45 shadow-[inset_0_1px_0_rgba(148,163,184,.08)]">
            <div className="border-b border-slate-800 px-4 py-3">
              <p className="text-sm font-medium text-slate-200">Chat com BrainAgent</p>
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
              {chatMessages.map((msg, idx) => (
                <div
                  key={`${msg.role}-${idx}`}
                  className={`rounded-lg px-3 py-2 text-sm ${
                    msg.role === "brainagent"
                      ? "bg-cyan-950/30 text-cyan-100 ring-1 ring-cyan-700/30"
                      : "bg-slate-950 text-slate-200 ring-1 ring-slate-700"
                  }`}
                >
                  {msg.content}
                </div>
              ))}
              {chatLoading ? (
                <div className="rounded-lg bg-slate-950 px-3 py-2 text-sm text-slate-400 ring-1 ring-slate-700">
                  BrainAgent esta pensando...
                </div>
              ) : null}
            </div>
            <div className="border-t border-slate-800 p-3">
              <div className="flex gap-2">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void sendChatMessage();
                    }
                  }}
                  placeholder="Pergunte algo ao BrainAgent..."
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-600/70"
                />
                <button
                  type="button"
                  onClick={() => void sendChatMessage()}
                  disabled={chatLoading || !chatInput.trim()}
                  className="rounded-lg bg-cyan-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-cyan-500 disabled:opacity-50"
                >
                  Enviar
                </button>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </Section>
  );
}

export default function LessonPage() {
  const params = useParams();
  const lessonId = String(params.id);

  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [step, setStep] = useState<Step>("hook");
  const [unlockedMax, setUnlockedMax] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storageKey = `lesson:${lessonId}:unlock`;
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (!raw) return;
      const value = Number.parseInt(raw, 10);
      if (Number.isFinite(value) && value >= 0 && value <= STEP_ORDER.length - 1) {
        setUnlockedMax(value);
      }
    } catch {
      // ignore browser storage failure
    }
  }, [lessonId]);

  useEffect(() => {
    try {
      sessionStorage.setItem(`lesson:${lessonId}:unlock`, String(unlockedMax));
    } catch {
      // ignore browser storage failure
    }
  }, [lessonId, unlockedMax]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await getAuthToken();
        if (!token) {
          if (!cancelled) setError("Sessao expirada. Faça login novamente.");
          return;
        }
        const loaded = await apiFetch<LessonDetail>(`/lessons/${lessonId}`, token);
        await apiFetch(`/lessons/${lessonId}/start`, token, { method: "POST" });
        if (!cancelled) {
          setLesson(loaded);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Erro ao carregar aula.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [lessonId]);

  function unlockAndGo(next: Step) {
    const idx = stepIndex(next);
    setUnlockedMax((prev) => Math.max(prev, idx));
    setStep(next);
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-rose-200">
        <p className="font-semibold">Falha ao abrir aula</p>
        <p className="mt-1 text-sm">{error}</p>
      </div>
    );
  }

  if (!lesson) {
    return <p className="text-slate-400">Carregando experiencia BrainAgent...</p>;
  }

  return (
    <div className="space-y-7">
      <header className="rounded-2xl border border-slate-800/90 bg-gradient-to-b from-slate-950/85 to-slate-950/70 p-6 shadow-[0_16px_60px_-35px_rgba(0,200,150,0.9)]">
        <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{lesson.id}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-100">{lesson.title}</h1>
        {lesson.subtitle ? <p className="mt-2 text-slate-400">{lesson.subtitle}</p> : null}
        <div className="mt-5 flex flex-wrap gap-2">
          <BrainAgentBadge mode={null} />
          {STEP_ORDER.map((entry) => {
            const idx = stepIndex(entry);
            const locked = idx > unlockedMax;
            const active = entry === step;
            return (
              <button
                key={entry}
                type="button"
                disabled={locked}
                onClick={() => setStep(entry)}
                className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                  locked
                    ? "cursor-not-allowed bg-slate-900 text-slate-600 ring-1 ring-slate-800"
                    : active
                      ? "bg-cyan-600/20 text-cyan-100 ring-1 ring-cyan-500/50"
                      : "bg-slate-900 text-slate-300 ring-1 ring-slate-700 hover:bg-slate-800"
                }`}
              >
                {STEP_LABELS[entry]}
              </button>
            );
          })}
        </div>
      </header>

      {step === "hook" ? (
        <HookSection title={lesson.title} config={lesson.hook_config} onContinue={() => unlockAndGo("widget")} />
      ) : null}
      {step === "widget" ? <WidgetSection onContinue={() => unlockAndGo("kb")} /> : null}
      {step === "kb" ? <KbSection content={lesson.kb_content} onContinue={() => unlockAndGo("exercise")} /> : null}
      {step === "exercise" ? <ExerciseSection lessonId={lesson.id} lessonTitle={lesson.title} /> : null}
    </div>
  );
}
