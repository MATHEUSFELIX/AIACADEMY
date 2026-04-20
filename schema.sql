-- ============================================================
-- MasterAI Academy — PostgreSQL Schema
-- Aplicar em ordem. Nunca editar migration já aplicada.
-- Versão: 1.0.0
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- busca textual

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE student_level AS ENUM (
  'level_0', 'level_1', 'level_2', 'level_3', 'level_4',
  'level_5', 'level_6', 'level_7', 'level_8', 'level_9', 'level_10'
);

CREATE TYPE student_profile AS ENUM (
  'analytics', 'marketing', 'strategy', 'c_level', 'produto'
);

CREATE TYPE lesson_module AS ENUM ('A', 'B', 'C', 'D', 'E', 'ZERO');

CREATE TYPE lesson_status AS ENUM (
  'locked', 'available', 'in_progress', 'completed'
);

CREATE TYPE exercise_variant AS ENUM (
  'scaffolded', 'padrao', 'desafio'
);

CREATE TYPE diagnostic_block AS ENUM ('A', 'B', 'C', 'D');

CREATE TYPE diagnostic_status AS ENUM (
  'not_started', 'in_progress', 'completed'
);

-- ============================================================
-- STUDENTS
-- ============================================================

CREATE TABLE students (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  auth_user_id      UUID NOT NULL UNIQUE,  -- Supabase auth.users.id
  name              VARCHAR(150) NOT NULL,
  email             VARCHAR(255) NOT NULL UNIQUE,
  profile           student_profile,        -- definido no onboarding
  current_level     student_level DEFAULT 'level_0',
  total_xp          INTEGER NOT NULL DEFAULT 0,
  streak_days       INTEGER NOT NULL DEFAULT 0,
  last_activity_at  TIMESTAMPTZ,
  diagnostic_status diagnostic_status NOT NULL DEFAULT 'not_started',
  onboarding_done   BOOLEAN NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_students_auth_user ON students(auth_user_id);
CREATE INDEX idx_students_email ON students(email);

-- ============================================================
-- LESSONS
-- ============================================================

CREATE TABLE lessons (
  id              VARCHAR(80) PRIMARY KEY,  -- ex: "did-diferenca-diferencas"
  title           VARCHAR(200) NOT NULL,
  subtitle        VARCHAR(300),
  module          lesson_module NOT NULL,
  level_number    SMALLINT NOT NULL CHECK (level_number BETWEEN 0 AND 10),
  order_in_level  SMALLINT NOT NULL DEFAULT 1,
  xp_reward       SMALLINT NOT NULL DEFAULT 100,
  duration_min    SMALLINT NOT NULL DEFAULT 30,  -- duração estimada em minutos

  -- Conteúdo estruturado (JSON seguindo lesson-schema.json)
  hook_config     JSONB NOT NULL,    -- cenas do hook animado
  widget_config   JSONB NOT NULL,    -- configuração do widget interativo
  kb_content      JSONB NOT NULL,    -- conteúdo das 4 abas da KB
  exercise_base   JSONB NOT NULL,    -- exercício base (será adaptado pelo BrainAgent)

  -- Metadados pedagógicos
  prerequisites   VARCHAR(80)[] NOT NULL DEFAULT '{}',  -- IDs de lessons
  connections     VARCHAR(80)[] NOT NULL DEFAULT '{}',   -- conceitos relacionados
  kb_confidence   NUMERIC(3,2) NOT NULL DEFAULT 0.90 CHECK (kb_confidence BETWEEN 0 AND 1),
  kb_entropy      NUMERIC(4,2) NOT NULL DEFAULT 5.0,

  -- Controle
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_lessons_module ON lessons(module);
CREATE INDEX idx_lessons_level ON lessons(level_number);
CREATE INDEX idx_lessons_active ON lessons(is_active) WHERE is_active = TRUE;

-- ============================================================
-- STUDENT LESSON PROGRESS
-- ============================================================

CREATE TABLE student_lesson_progress (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id      UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  lesson_id       VARCHAR(80) NOT NULL REFERENCES lessons(id),
  status          lesson_status NOT NULL DEFAULT 'locked',

  -- Scores por dimensão (0.0 a 1.0)
  score_technical     NUMERIC(3,2) CHECK (score_technical BETWEEN 0 AND 1),
  score_methodological NUMERIC(3,2) CHECK (score_methodological BETWEEN 0 AND 1),
  score_antipatterns  NUMERIC(3,2) CHECK (score_antipatterns BETWEEN 0 AND 1),
  score_interpretation NUMERIC(3,2) CHECK (score_interpretation BETWEEN 0 AND 1),
  score_composite     NUMERIC(3,2) CHECK (score_composite BETWEEN 0 AND 1),

  -- Metadados do exercício
  variant_used    exercise_variant,
  used_hint       BOOLEAN NOT NULL DEFAULT FALSE,
  xp_earned       SMALLINT NOT NULL DEFAULT 0,
  attempts        SMALLINT NOT NULL DEFAULT 0,

  -- Atualização de confiança bayesiana (reflexo na Semantic Memory)
  confidence_before NUMERIC(3,2),
  confidence_after  NUMERIC(3,2),

  -- Timestamps
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE(student_id, lesson_id)
);

CREATE INDEX idx_slp_student ON student_lesson_progress(student_id);
CREATE INDEX idx_slp_lesson ON student_lesson_progress(lesson_id);
CREATE INDEX idx_slp_status ON student_lesson_progress(student_id, status);

-- ============================================================
-- EPISODIC MEMORY
-- (histórico detalhado de cada interação — BrainAgent V2)
-- ============================================================

CREATE TABLE episodic_memory (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  lesson_id   VARCHAR(80) REFERENCES lessons(id),

  -- Descrição do episódio
  context     TEXT NOT NULL,   -- o que estava acontecendo
  action      VARCHAR(100) NOT NULL,  -- o que o aluno fez
  outcome     TEXT,            -- resultado
  valence     NUMERIC(3,2) NOT NULL DEFAULT 0.5 CHECK (valence BETWEEN 0 AND 1),
  importance  NUMERIC(3,2) NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),

  -- Shannon entropy do episódio (pruning)
  entropy     NUMERIC(4,2),

  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_episodic_student ON episodic_memory(student_id);
CREATE INDEX idx_episodic_student_lesson ON episodic_memory(student_id, lesson_id);
CREATE INDEX idx_episodic_created ON episodic_memory(student_id, created_at DESC);

-- ============================================================
-- PROCEDURAL MEMORY
-- (padrões aprendidos sobre como cada aluno aprende)
-- ============================================================

CREATE TABLE procedural_memory (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,

  pattern     TEXT NOT NULL,        -- descrição do padrão
  category    VARCHAR(50) NOT NULL, -- 'learning_style', 'preference', 'weakness', 'strength'
  confidence  NUMERIC(3,2) NOT NULL DEFAULT 0.5 CHECK (confidence BETWEEN 0 AND 1),
  evidence_count INTEGER NOT NULL DEFAULT 1,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_procedural_student ON procedural_memory(student_id);
CREATE INDEX idx_procedural_category ON procedural_memory(student_id, category);

-- ============================================================
-- DIAGNOSTIC SESSIONS
-- ============================================================

CREATE TABLE diagnostic_sessions (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  status      diagnostic_status NOT NULL DEFAULT 'in_progress',

  -- Blocos completados e resultados
  block_a_completed BOOLEAN NOT NULL DEFAULT FALSE,
  block_b_completed BOOLEAN NOT NULL DEFAULT FALSE,
  block_c_completed BOOLEAN NOT NULL DEFAULT FALSE,
  block_d_completed BOOLEAN NOT NULL DEFAULT FALSE,

  -- Resultado
  identified_level  student_level,
  brainagent_notes  TEXT,  -- análise qualitativa do BrainAgent

  -- Histórico completo da conversa (para o BrainAgent usar como contexto)
  conversation      JSONB NOT NULL DEFAULT '[]',

  started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_diagnostic_student ON diagnostic_sessions(student_id);

-- ============================================================
-- EXERCISE SUBMISSIONS
-- (cada resposta do aluno a um exercício)
-- ============================================================

CREATE TABLE exercise_submissions (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id    UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  lesson_id     VARCHAR(80) NOT NULL REFERENCES lessons(id),
  attempt_number SMALLINT NOT NULL DEFAULT 1,

  -- Conteúdo
  student_answer TEXT NOT NULL,
  exercise_variant exercise_variant NOT NULL,
  generated_exercise JSONB NOT NULL,  -- o exercício que o BrainAgent gerou

  -- Avaliação
  score_technical      NUMERIC(3,2),
  score_methodological NUMERIC(3,2),
  score_antipatterns   NUMERIC(3,2),
  score_interpretation NUMERIC(3,2),
  score_composite      NUMERIC(3,2),
  brainagent_feedback  TEXT,

  -- Metadata
  used_hint   BOOLEAN NOT NULL DEFAULT FALSE,
  xp_earned   SMALLINT NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_submissions_student ON exercise_submissions(student_id);
CREATE INDEX idx_submissions_lesson ON exercise_submissions(lesson_id);
CREATE INDEX idx_submissions_student_lesson ON exercise_submissions(student_id, lesson_id);

-- ============================================================
-- STUDENT OBJECTIVES
-- (Objective Layer do BrainAgent V2)
-- ============================================================

CREATE TABLE student_objectives (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,

  goal        TEXT NOT NULL,
  priority    SMALLINT NOT NULL DEFAULT 1,
  progress    NUMERIC(3,2) NOT NULL DEFAULT 0.0 CHECK (progress BETWEEN 0 AND 1),
  deadline    DATE,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_objectives_student ON student_objectives(student_id, is_active);

-- ============================================================
-- XP TRANSACTIONS
-- (histórico de ganho de XP para auditoria e streak)
-- ============================================================

CREATE TABLE xp_transactions (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  amount      SMALLINT NOT NULL,  -- pode ser negativo (hint usado)
  reason      VARCHAR(100) NOT NULL,
  lesson_id   VARCHAR(80) REFERENCES lessons(id),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_xp_student ON xp_transactions(student_id);
CREATE INDEX idx_xp_student_date ON xp_transactions(student_id, created_at DESC);

-- ============================================================
-- TRIGGERS — updated_at automático
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_students_updated
  BEFORE UPDATE ON students
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_lessons_updated
  BEFORE UPDATE ON lessons
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_slp_updated
  BEFORE UPDATE ON student_lesson_progress
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_procedural_updated
  BEFORE UPDATE ON procedural_memory
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_objectives_updated
  BEFORE UPDATE ON student_objectives
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- VIEWS ÚTEIS
-- ============================================================

-- Visão geral do progresso do aluno
CREATE VIEW student_overview AS
SELECT
  s.id AS student_id,
  s.name,
  s.profile,
  s.current_level,
  s.total_xp,
  s.streak_days,
  COUNT(slp.id) FILTER (WHERE slp.status = 'completed') AS lessons_completed,
  COUNT(slp.id) FILTER (WHERE slp.status = 'available') AS lessons_available,
  COUNT(slp.id) FILTER (WHERE slp.status = 'locked') AS lessons_locked,
  AVG(slp.score_composite) FILTER (WHERE slp.status = 'completed') AS avg_score,
  MAX(slp.completed_at) AS last_lesson_at
FROM students s
LEFT JOIN student_lesson_progress slp ON slp.student_id = s.id
GROUP BY s.id, s.name, s.profile, s.current_level, s.total_xp, s.streak_days;

-- Próxima aula recomendada (candidatos desbloqueados não concluídos)
CREATE VIEW available_lessons_per_student AS
SELECT
  s.id AS student_id,
  l.id AS lesson_id,
  l.title,
  l.level_number,
  l.order_in_level,
  l.xp_reward,
  slp.status
FROM students s
JOIN student_lesson_progress slp ON slp.student_id = s.id
JOIN lessons l ON l.id = slp.lesson_id
WHERE slp.status = 'available'
  AND l.is_active = TRUE;

-- ============================================================
-- SEED: Exemplo de aula Nível 0 (inserir via seed script)
-- ============================================================
-- As aulas são inseridas via script Python que lê os JSONs de
-- backend/content/ e popula a tabela lessons.
-- Não inserir aulas manualmente neste arquivo.

-- ============================================================
-- ROW LEVEL SECURITY (Supabase)
-- ============================================================

ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_lesson_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodic_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE procedural_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercise_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_objectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE xp_transactions ENABLE ROW LEVEL SECURITY;

-- Alunos só veem seus próprios dados
CREATE POLICY students_self ON students
  FOR ALL USING (auth.uid() = auth_user_id);

CREATE POLICY slp_self ON student_lesson_progress
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY episodic_self ON episodic_memory
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY procedural_self ON procedural_memory
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY submissions_self ON exercise_submissions
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY objectives_self ON student_objectives
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

CREATE POLICY xp_self ON xp_transactions
  FOR ALL USING (student_id = (
    SELECT id FROM students WHERE auth_user_id = auth.uid()
  ));

-- Aulas são públicas para leitura (autenticados)
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
CREATE POLICY lessons_read ON lessons
  FOR SELECT USING (auth.role() = 'authenticated' AND is_active = TRUE);
