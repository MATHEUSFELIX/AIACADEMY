export const LEVEL_NAMES: Record<number, string> = {
  0: "Alfabetização",
  1: "SQL & Delta Lake",
  2: "Ferramentas Básicas",
  3: "Primeiro Modelo",
  4: "Ensemble & Avaliação",
  5: "LightGBM & DiD",
  6: "Eval Framework",
  7: "SHAP & Clustering",
  8: "MLflow & Storytelling",
  9: "Feature Store",
  10: "Phase Transition",
};

export const LESSON_STATUS_LABELS: Record<string, string> = {
  completed: "Concluída",
  in_progress: "Em progresso",
  available: "Disponível",
  locked: "Bloqueada",
};

export const PROFILES: Record<string, string> = {
  analytics: "Analytics",
  marketing: "Marketing",
  strategy: "Strategy",
  c_level: "C-Level",
  produto: "Produto",
};

export const XP_THRESHOLDS = {
  PASS: 0.75,
  ADVANCE_LEVEL: 0.8,
  PERFECT: 0.95,
} as const;
