"use client"

import { useState } from "react"

interface Mode {
  mode: string
  name: string
  description: string
  emoji: string
  icon: string
}

interface Recommendation {
  recommended_mode: string
  reason: string
}

interface ModeSelectorProps {
  lessonId: string
  studentId: string
  onModeSelected: (mode: string) => void
  isLoading?: boolean
}

export default function ModeSelector({
  lessonId,
  studentId: _studentId,
  onModeSelected,
  isLoading = false,
}: ModeSelectorProps) {
  const [modes] = useState<Mode[]>(BRAINAGENT_MODES)
  const [selectedMode, setSelectedMode] = useState<string | null>(null)
  const [showRecommendation, setShowRecommendation] = useState(false)
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)

  const selectedModeData = modes.find((mode) => mode.mode === selectedMode) ?? null

  const requestRecommendation = (): void => {
    const recommendedMode = recommendModeForLesson(lessonId, _studentId)
    const recommendedModeData = modes.find((mode) => mode.mode === recommendedMode)
    setRecommendation({
      recommended_mode: recommendedMode,
      reason: `Para esta aula, o modo ${recommendedModeData?.name ?? recommendedMode} equilibra autonomia e orientacao sem depender de chamadas extras ao backend.`,
    })
    setShowRecommendation(true)
  }

  const handleModeSelection = (mode: string) => {
    setSelectedMode(mode)
    setShowRecommendation(false)
    onModeSelected(mode)
  }

  if (modes.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6 text-center">
        <p className="text-sm text-slate-400">Nenhum modo do BrainAgent disponivel agora.</p>
      </div>
    )
  }

  return (
    <div className="w-full max-w-5xl mx-auto rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-[0_14px_50px_-30px_rgba(0,200,150,0.9)]">
      <div className="mb-8">
        <p className="text-[11px] uppercase tracking-[0.22em] text-cyan-400/80">BrainAgent Studio</p>
        <h2 className="mt-2 text-2xl font-bold text-slate-100">Como voce quer aprender esta aula?</h2>
        <p className="mt-2 text-sm text-slate-400">
          Escolha um modo manualmente ou peça recomendacao adaptativa ao BrainAgent.
        </p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {modes.map((mode) => (
          <button
            key={mode.mode}
            type="button"
            onClick={() => handleModeSelection(mode.mode)}
            className={`group relative overflow-hidden rounded-xl border p-5 text-left transition-all ${
              selectedMode === mode.mode
                ? "border-cyan-400/70 bg-gradient-to-br from-cyan-500/10 to-emerald-500/10 shadow-[0_0_0_1px_rgba(34,211,238,.25)]"
                : "border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/70"
            }`}
          >
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-500/0 via-cyan-500/0 to-emerald-500/0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-hover:from-cyan-500/5 group-hover:to-emerald-500/5" />

            <div className="relative z-10">
              <div className="mb-3 flex items-center justify-between">
                <div className="text-3xl">{mode.emoji || "🧠"}</div>
                <span className="rounded-full border border-slate-700 bg-slate-950/90 px-2 py-1 text-[10px] uppercase tracking-wider text-slate-400">
                  {mode.icon || mode.mode}
                </span>
              </div>
              <h3 className="mb-2 text-base font-semibold text-slate-100">{mode.name}</h3>
              <p className="text-sm leading-snug text-slate-400">{mode.description}</p>
            </div>

            {selectedMode === mode.mode && (
              <div className="relative z-10 mt-4 inline-flex items-center gap-2 rounded-full border border-cyan-500/50 bg-cyan-500/15 px-3 py-1 text-xs font-semibold text-cyan-200">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-300" />
                Modo selecionado
              </div>
            )}
          </button>
        ))}
      </div>

      {!showRecommendation ? (
        <div className="mb-6 flex flex-col items-center gap-2">
          <button
            type="button"
            onClick={requestRecommendation}
            disabled={isLoading}
            className="rounded-lg border border-cyan-500/40 bg-gradient-to-r from-cyan-500/20 to-indigo-500/20 px-6 py-3 text-sm font-semibold text-cyan-100 transition hover:from-cyan-500/30 hover:to-indigo-500/30 disabled:opacity-50"
          >
            Nao sei qual modo escolher
          </button>
          <p className="text-xs text-slate-500">
            O BrainAgent escolhe um modo consistente para esta etapa sem interromper o fluxo da aula.
          </p>
        </div>
      ) : null}

      {showRecommendation && recommendation ? (
        <div className="mb-6 rounded-xl border border-cyan-700/50 bg-gradient-to-br from-cyan-950/40 to-slate-900 p-5">
            <div className="flex items-start gap-4">
              <span className="text-3xl">🧠</span>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-cyan-100">Recomendacao do BrainAgent</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{recommendation.reason}</p>

                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => handleModeSelection(recommendation.recommended_mode)}
                    className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
                  >
                    Aplicar {recommendation.recommended_mode}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowRecommendation(false)}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800"
                  >
                    Ver todos os modos
                  </button>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowRecommendation(false)}
                className="text-xl text-slate-500 transition hover:text-slate-300"
                aria-label="Fechar recomendacao"
              >
                ×
              </button>
            </div>
        </div>
      ) : null}

      {selectedMode && selectedModeData ? (
        <div className="rounded-xl border border-emerald-700/50 bg-emerald-950/20 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-emerald-300/80">
                  Modo ativo do BrainAgent
                </p>
                <p className="mt-1 text-sm text-slate-200">
                  {selectedModeData.emoji} <span className="font-semibold">{selectedModeData.name}</span>
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Pode trocar o modo a qualquer momento antes de gerar ou reenviar exercicios.
                </p>
              </div>
              <button
                type="button"
                onClick={() => onModeSelected(selectedMode)}
                disabled={isLoading}
                className="rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
              >
                {isLoading ? "Iniciando..." : "Continuar com este modo"}
              </button>
            </div>
        </div>
      ) : null}
    </div>
  )
}

const BRAINAGENT_MODES: Mode[] = [
  {
    mode: "socratic",
    name: "Socratico",
    description: "O BrainAgent conduz a resolucao com perguntas curtas para testar entendimento antes da resposta final.",
    emoji: "?",
    icon: "SOCR",
  },
  {
    mode: "streaming",
    name: "Raciocinio guiado",
    description: "Acompanhe uma linha de raciocinio estruturada para transformar dados em decisao de negocio.",
    emoji: ">",
    icon: "FLOW",
  },
  {
    mode: "inner_monologue",
    name: "Autonomia",
    description: "Receba intervencoes minimas, com foco em independencia e revisao das proprias hipoteses.",
    emoji: "#",
    icon: "AUTO",
  },
  {
    mode: "progressive",
    name: "Progressivo",
    description: "Comece com apoio maior e desbloqueie menos pistas conforme demonstrar dominio do conceito.",
    emoji: "+",
    icon: "PROG",
  },
  {
    mode: "competitive",
    name: "Duelo de solucoes",
    description: "Compare duas abordagens possiveis e escolha a mais robusta para o contexto fintech.",
    emoji: "x",
    icon: "VS",
  },
  {
    mode: "moment_gated",
    name: "Ajuda no momento certo",
    description: "O BrainAgent segura respostas prontas e libera orientacao quando o exercicio realmente pede.",
    emoji: "!",
    icon: "GATE",
  },
]

function recommendModeForLesson(lessonId: string, studentId: string): string {
  const seed = `${lessonId}:${studentId}`
  const total = Array.from(seed).reduce((sum, char) => sum + char.charCodeAt(0), 0)
  const rotation = ["progressive", "socratic", "moment_gated", "inner_monologue"]
  return rotation[total % rotation.length]
}
