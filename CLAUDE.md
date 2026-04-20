# CLAUDE.md — MasterAI Academy

> Leia este documento inteiro antes de escrever qualquer linha de código.
> Releia no início de cada nova sessão.

---

## 1. O QUE É ESTE PROJETO

MasterAI Academy é uma plataforma de aprendizado de IA e dados para o time interno de consultoria de Matheus Felix. O professor é o BrainAgent V2 — um agente com memória hierárquica que adapta o conteúdo ao nível e perfil de cada aluno.

**Não é um produto comercial.** É uma ferramenta interna. Isso significa:
- Sem billing, sem multi-tenant complexo, sem SLA de enterprise
- Prioridade: funcionar bem para ~20 pessoas, não escalar para 10.000
- Velocidade de desenvolvimento > perfeição arquitetural prematura

---

## 2. STACK — NUNCA MUDE SEM APROVAÇÃO EXPLÍCITA

```
Frontend     Next.js 14 (App Router) + Tailwind CSS
Backend      FastAPI (Python 3.11+)
Banco        PostgreSQL via Supabase (banco + auth + storage)
Vetorial     ChromaDB (memória semântica do BrainAgent)
IA           Anthropic SDK — claude-sonnet-4-20250514 APENAS
Deploy       Vercel (frontend) + Railway (backend)
Dev local    Docker Compose
Testes       Pytest (backend) + Playwright (E2E)
```

**Regras de stack:**
- NUNCA usar `localStorage` para estado de aluno — vai para o banco
- NUNCA expor `ANTHROPIC_API_KEY` no frontend — toda chamada ao Claude passa pelo backend
- NUNCA usar `any` em TypeScript — tipagem estrita sempre
- NUNCA usar `SELECT *` em queries SQL — sempre listar colunas explicitamente
- NUNCA usar o comando `SET` em SQL (restrição do ambiente Databricks herdada)
- Sempre usar `async/await`, nunca `.then()` encadeado

---

## 3. ESTRUTURA DE PASTAS

```
masterai-academy/
├── CLAUDE.md                    ← este arquivo
├── docker-compose.yml
├── .env.example
│
├── frontend/                    ← Next.js
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── signup/
│   │   ├── (app)/
│   │   │   ├── layout.tsx       ← layout autenticado
│   │   │   ├── dashboard/       ← home do aluno
│   │   │   ├── diagnostic/      ← assessment de entrada
│   │   │   ├── lesson/[id]/     ← aula individual
│   │   │   ├── kb/              ← knowledge base
│   │   │   └── progress/        ← progresso e memória
│   │   └── api/                 ← API routes Next.js (proxies apenas)
│   ├── components/
│   │   ├── ui/                  ← componentes base (Button, Card, Badge)
│   │   ├── lesson/              ← Hook, Widget, KB, Exercise, Result
│   │   ├── diagnostic/          ← componentes do assessment
│   │   ├── dashboard/           ← trilhas, progresso, próxima aula
│   │   └── kb/                  ← grafo semântico, wiki cards
│   ├── lib/
│   │   ├── api.ts               ← cliente HTTP para o backend
│   │   ├── types.ts             ← todos os tipos TypeScript
│   │   └── constants.ts         ← constantes globais
│   └── public/
│
├── backend/                     ← FastAPI
│   ├── main.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── diagnostic.py
│   │   ├── lessons.py
│   │   ├── progress.py
│   │   ├── brainagent.py
│   │   └── kb.py
│   ├── services/
│   │   ├── brainagent_service.py   ← toda lógica do BrainAgent
│   │   ├── diagnostic_service.py   ← lógica do assessment
│   │   ├── progress_service.py     ← cálculo de XP, nível, desbloqueio
│   │   └── content_service.py      ← leitura de aulas do banco
│   ├── models/
│   │   ├── database.py          ← SQLAlchemy models
│   │   └── schemas.py           ← Pydantic schemas
│   ├── memory/
│   │   ├── episodic.py          ← episodic memory (PostgreSQL)
│   │   ├── semantic.py          ← semantic memory (ChromaDB)
│   │   ├── procedural.py        ← procedural memory (PostgreSQL)
│   │   └── working.py           ← working memory (Redis ou in-memory)
│   ├── content/                 ← aulas em JSON
│   │   ├── level-0/             ← 8 aulas de alfabetização
│   │   ├── level-1/             ← SQL, Delta Lake
│   │   ├── level-2/             ← ferramentas básicas
│   │   └── ...
│   └── tests/
│
└── docs/
    ├── CLAUDE.md                ← este arquivo
    ├── schema.sql               ← schema do banco
    ├── api-contract.md          ← contrato de API
    └── lesson-schema.json       ← schema de conteúdo
```

---

## 4. CONVENÇÕES DE CÓDIGO

### Python (backend)
```python
# Nomenclatura: snake_case para tudo
# Funções assíncronas sempre que houver I/O
async def get_student_progress(student_id: str) -> StudentProgress:
    ...

# Type hints obrigatórios em todas as funções
# Docstring obrigatória em services e funções públicas
# Exceções sempre com mensagem descritiva
raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found")

# Logging estruturado — nunca print()
import logging
logger = logging.getLogger(__name__)
logger.info("Lesson completed", extra={"student_id": sid, "lesson_id": lid})
```

### TypeScript (frontend)
```typescript
// Nomenclatura: camelCase para variáveis/funções, PascalCase para componentes e tipos
// Props sempre tipadas com interface
interface LessonCardProps {
  lesson: Lesson;
  onComplete: (score: number) => void;
}

// Nunca usar 'any' — use 'unknown' se necessário e faça type guard
// Fetches sempre via lib/api.ts — nunca fetch() direto nos componentes
// Estados de loading e error sempre tratados explicitamente
```

### SQL
```sql
-- Sempre nomear colunas explicitamente — nunca SELECT *
-- Sempre usar índices em foreign keys e colunas de busca frequente
-- Migrations versionadas — nunca editar migration já aplicada
-- Comentários em queries complexas
```

---

## 5. FLUXO DO ALUNO — ENTENDER ANTES DE CODAR

```
1. PRIMEIRO ACESSO
   Aluno cria conta → vai direto para o Diagnóstico
   Diagnóstico: 10-15 min, 3-4 blocos de perguntas adaptativas
   BrainAgent avalia respostas → determina nível 0, 1, 2 ou 3+
   Resultado: nível identificado + caminho personalizado criado

2. DASHBOARD
   Mostra: trilha atual, próxima aula, progresso, XP, memória ativa
   BrainAgent exibe mensagem personalizada baseada no histórico
   Conceitos desbloqueados vs bloqueados visualmente

3. AULA (4 etapas sequenciais)
   Etapa 1 — Hook: cenário animado SVG (2 min)
   Etapa 2 — Widget: interativo com sliders/gráficos (5-8 min)
   Etapa 3 — KB: referência estruturada em abas (3-5 min)
   Etapa 4 — Exercício: código/raciocínio avaliado pelo BrainAgent (10-15 min)
   Resultado: XP, score, confiança bayesiana atualizada, próxima aula

4. PÓS-AULA
   Score salvo no banco → Episodic Memory atualizada
   Procedural Memory atualizada com o que funcionou
   Objetivo Layer verifica progresso
   Conceitos dependentes desbloqueados se score >= 0.75
   BrainAgent determina próxima aula recomendada
```

---

## 6. BRAINAGENT — REGRAS DE USO

O BrainAgent é o núcleo da plataforma. Toda interação com Claude passa pelo `brainagent_service.py`.

**Regras:**
- Model fixo: `claude-sonnet-4-20250514` — nunca mudar sem aprovação
- Max tokens: 1500 para avaliações de exercício, 800 para chat, 500 para recomendações
- System prompt montado dinamicamente com: perfil do aluno + histórico relevante + conceito atual
- NUNCA chamar a API do Claude direto do frontend
- Cache de respostas frequentes (recomendação de próxima aula) — TTL 1 hora
- Rate limiting: máximo 20 chamadas por aluno por hora

**As 4 camadas de memória:**
```
Working Memory   → Redis (TTL 24h) — contexto da sessão atual
Episodic Memory  → PostgreSQL — histórico de todas as aulas e scores
Semantic Memory  → ChromaDB — grafo de conceitos com confiança bayesiana
Procedural Memory → PostgreSQL — padrões aprendidos por aluno
```

---

## 7. CONTEÚDO DAS AULAS — COMO FUNCIONA

Aulas são arquivos JSON em `backend/content/level-X/`. Não são geradas dinamicamente — são estáticas, carregadas no banco na inicialização.

O BrainAgent **não gera** o conteúdo da aula. Ele:
1. Lê o conteúdo estático (hook, widget config, KB, exercício base)
2. Adapta o **exercício** ao perfil do aluno via `generate_exercise()`
3. **Avalia** a resposta do aluno via `evaluate_exercise()`
4. **Recomenda** a próxima aula via `recommend_next()`

Isso mantém consistência pedagógica — o conteúdo core não muda, só o exercício é personalizado.

---

## 8. NÍVEIS E DESBLOQUEIO

```
Nível 0 (8 aulas)  — Alfabetização: sem código, visual puro
Nível 1 (2 aulas)  — SQL + Delta Lake
Nível 2 (4 aulas)  — Ferramentas básicas
Nível 3 (3 aulas)  — Primeiro modelo
Nível 4 (2 aulas)  — Ensemble + Avaliação
Nível 5 (3 aulas)  — LightGBM + DiD + Charts
Nível 6 (5 aulas)  — Eval Framework + Causal
Nível 7 (7 aulas)  — SHAP + Clustering + Shannon + Survival + X-Learner
Nível 8 (4 aulas)  — MLflow + nuFormer + Storytelling + Anomaly
Nível 9 (6 aulas)  — Feature Store + Lineage + Alertas + Graph + Fractal
Nível 10 (3 aulas) — Phase Transition + Louvain + Dim. Fractal
```

**Regra de desbloqueio:** todos os pré-requisitos com score >= 0.75.
**Regra de avanço de nível:** 80% das aulas do nível atual com score >= 0.75.

---

## 9. VARIANTES DE EXERCÍCIO POR SCORE HISTÓRICO

```
score_medio < 0.60  → variante "scaffolded"
  Código quase completo, aluno preenche lacunas
  Dicas automáticas no enunciado
  Dataset menor, menos variáveis

0.60 <= score < 0.80 → variante "padrao"
  Enunciado completo, código em branco
  Hints disponíveis mas custam -10 XP
  Dataset realista

score >= 0.80        → variante "desafio"
  Twist no enunciado (suposição violada, bug proposital)
  Sem hints disponíveis
  Dataset com problemas para o aluno detectar
```

---

## 10. VARIANTES DE EXERCÍCIO POR PERFIL

O campo `perfil` do aluno (definido no onboarding) determina o contexto:

```
analytics    → exemplos PySpark, Delta Lake, Databricks SQL
marketing    → campanhas, conversão, segmentação, canais
strategy     → slides executivos, business case, ROI
c_level      → interpretação de resultados, decisão, governança
produto      → métricas de produto, funil, A/B Testing
```

---

## 11. DIAGNÓSTICO DE ENTRADA — LÓGICA

O diagnóstico tem 4 blocos, cada um com 2-4 perguntas:

```
Bloco A — Alfabetização (sempre exibido)
  Detecta: sabe o que é dado, tabela, métrica
  Se passa → vai para Bloco B
  Se não passa → nível 0, encerra diagnóstico

Bloco B — SQL e Ferramentas
  Detecta: conhece SQL, entende pipeline de dados
  Se passa → vai para Bloco C
  Se não passa → nível 1, encerra

Bloco C — Modelagem Básica
  Detecta: conhece conceito de modelo, overfitting, acurácia
  Se passa → vai para Bloco D
  Se não passa → nível 2, encerra

Bloco D — Causalidade e ML Avançado
  Detecta: intuição causal, conhece LightGBM, SHAP
  Resultado → nível 3, 4 ou 5+ dependendo das respostas
```

O diagnóstico é conversacional — o BrainAgent conduz via chat, não é formulário de múltipla escolha. As respostas são texto livre avaliadas pelo Claude.

---

## 12. XP E GAMIFICAÇÃO

```
Aula concluída (score >= 0.75)     → XP base da aula (80-150 XP)
Score perfeito (score >= 0.95)     → +20% XP bonus
Streak diário (7 dias seguidos)    → +50 XP/dia
Sem usar hints                     → +10 XP
Variante desafio concluída         → +30% XP bonus
Conceito desbloqueado              → notificação + animação
```

---

## 13. VARIÁVEIS DE AMBIENTE NECESSÁRIAS

```bash
# Backend (.env)
ANTHROPIC_API_KEY=sk-...
SUPABASE_URL=https://...supabase.co
SUPABASE_SERVICE_KEY=...
DATABASE_URL=postgresql://...
CHROMADB_HOST=localhost
CHROMADB_PORT=8001
REDIS_URL=redis://localhost:6379
SECRET_KEY=...  # JWT signing

# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=https://...supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000
# NUNCA colocar ANTHROPIC_API_KEY aqui
```

---

## 14. ORDEM DE DESENVOLVIMENTO — FASE 1 (MVP)

Implementar nesta ordem exata. Não pular etapas.

```
[ ] 1. Docker Compose com Postgres + ChromaDB + Redis
[ ] 2. Schema SQL aplicado (schema.sql)
[ ] 3. FastAPI base com health check
[ ] 4. Autenticação Supabase (login/signup)
[ ] 5. Seed das aulas no banco (49 conceitos, conteúdo JSON)
[ ] 6. Endpoint de diagnóstico + lógica do BrainAgent
[ ] 7. Tela de diagnóstico no frontend
[ ] 8. Dashboard do aluno (próxima aula, progresso)
[ ] 9. Tela de aula completa (4 etapas)
[ ] 10. Endpoint de avaliação de exercício
[ ] 11. Sistema de XP e desbloqueio
[ ] 12. Tela de Knowledge Base
[ ] 13. Tela de progresso e memória
[ ] 14. Deploy (Vercel + Railway)
```

---

## 15. O QUE NUNCA FAZER

- Nunca colocar lógica de negócio no frontend — vai para o backend
- Nunca chamar Claude diretamente do frontend
- Nunca fazer migration manual no banco — sempre via arquivo versionado
- Nunca commitar `.env` ou `.env.local`
- Nunca usar `console.log` em produção — usar logger estruturado
- Nunca ignorar erros silenciosamente — sempre logar e retornar erro descritivo
- Nunca criar endpoint sem autenticação (exceto `/health` e `/auth/*`)
- Nunca salvar resposta do aluno sem sanitizar input
- Nunca usar modelo Claude diferente de `claude-sonnet-4-20250514`
- Nunca quebrar o schema de `lesson-schema.json` — todas as aulas devem seguir o mesmo formato

---

## 16. CONTATO E CONTEXTO

**Dono do projeto:** Matheus Felix
**Stack favorito:** Python, PySpark, Databricks, Delta Lake
**Clientes de referência nos exemplos:** PicPay, Santander, Inter, C6 Bank, Mastercard Brasil
**Tom do BrainAgent:** professor sênior direto, sem elogios excessivos, exemplos sempre fintech
