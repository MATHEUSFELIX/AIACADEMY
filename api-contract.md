# API Contract — MasterAI Academy Backend

> Base URL: `http://localhost:8000` (dev) · `https://api.masterai.academy` (prod)
> Autenticação: Bearer token JWT (Supabase) em todas as rotas exceto `/health` e `/auth/*`
> Content-Type: `application/json` em todos os endpoints

---

## AUTENTICAÇÃO

Todas as requisições autenticadas devem incluir:
```
Authorization: Bearer <supabase_jwt_token>
```

O backend valida o token com Supabase e extrai o `student_id` correspondente.

---

## HEALTH

### GET /health
Verifica se a API está rodando.

**Response 200:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-04-18T10:00:00Z"
}
```

---

## AUTH ROUTES

### POST /auth/onboarding
Completa o onboarding do aluno após signup. Define nome e perfil.

**Request:**
```json
{
  "name": "João Silva",
  "profile": "analytics"
}
```

**Response 200:**
```json
{
  "student_id": "uuid",
  "name": "João Silva",
  "profile": "analytics",
  "onboarding_done": true,
  "next_step": "diagnostic"
}
```

**Errors:** 400 (profile inválido), 409 (onboarding já feito)

---

## DIAGNOSTIC ROUTES

### POST /diagnostic/start
Inicia uma nova sessão de diagnóstico. Retorna a primeira mensagem do BrainAgent.

**Request:** `{}` (vazio — student_id vem do JWT)

**Response 200:**
```json
{
  "session_id": "uuid",
  "message": "Olá! Vou fazer algumas perguntas para entender melhor seu nível...",
  "block": "A",
  "question_number": 1,
  "total_questions_estimate": "10-15"
}
```

**Errors:** 409 (diagnóstico já completado)

---

### POST /diagnostic/answer
Envia a resposta do aluno e recebe a próxima pergunta ou o resultado.

**Request:**
```json
{
  "session_id": "uuid",
  "answer": "Eu usaria SQL para filtrar os dados primeiro..."
}
```

**Response 200 — próxima pergunta:**
```json
{
  "type": "question",
  "message": "Boa resposta. Agora: você tem 1 milhão de linhas. Como você calcularia...",
  "block": "A",
  "question_number": 2
}
```

**Response 200 — diagnóstico concluído:**
```json
{
  "type": "completed",
  "identified_level": "level_1",
  "message": "Diagnóstico concluído! Você tem boa familiaridade com dados...",
  "summary": "Conhece SQL básico, nunca trabalhou com modelos de ML.",
  "recommended_path": {
    "start_lesson": "sql-motor-analise",
    "total_lessons": 47,
    "estimated_hours": 85
  }
}
```

**Errors:** 404 (session não encontrada), 400 (session já completada)

---

### GET /diagnostic/status
Verifica o status do diagnóstico do aluno logado.

**Response 200:**
```json
{
  "status": "completed",
  "identified_level": "level_1",
  "completed_at": "2026-04-18T10:30:00Z"
}
```

---

## STUDENT ROUTES

### GET /students/me
Retorna os dados completos do aluno logado.

**Response 200:**
```json
{
  "id": "uuid",
  "name": "João Silva",
  "email": "joao@empresa.com",
  "profile": "analytics",
  "current_level": "level_1",
  "total_xp": 450,
  "streak_days": 3,
  "last_activity_at": "2026-04-17T18:00:00Z",
  "diagnostic_status": "completed",
  "onboarding_done": true,
  "stats": {
    "lessons_completed": 5,
    "lessons_available": 3,
    "lessons_locked": 41,
    "avg_score": 0.81
  }
}
```

---

### GET /students/me/overview
Dashboard overview — dados para a tela principal.

**Response 200:**
```json
{
  "next_lesson": {
    "id": "quando-nao-usar-modelo",
    "title": "Quando NÃO usar modelo",
    "level_number": 2,
    "xp_reward": 100,
    "duration_min": 25
  },
  "brainagent_message": "Você travou em SQL Window Functions semana passada...",
  "current_level": {
    "level": "level_1",
    "progress_pct": 50,
    "lessons_done": 1,
    "lessons_total": 2
  },
  "recent_activity": [
    {
      "lesson_id": "sql-motor-analise",
      "title": "SQL Motor de Análise",
      "score": 0.88,
      "completed_at": "2026-04-17T18:00:00Z"
    }
  ],
  "memory_snapshot": {
    "procedural": [
      "Prefere exemplos com Delta Lake",
      "Aprende melhor com código antes da teoria"
    ],
    "concepts_mastered": 1,
    "concepts_in_progress": 0
  }
}
```

---

## LESSON ROUTES

### GET /lessons
Lista todas as aulas com o status do aluno logado.

**Query params:**
- `level` (optional): filtrar por nível (0-10)
- `module` (optional): filtrar por módulo (A, B, C, D, E, ZERO)
- `status` (optional): filtrar por status (locked, available, in_progress, completed)

**Response 200:**
```json
{
  "lessons": [
    {
      "id": "sql-motor-analise",
      "title": "SQL como Motor de Análise",
      "module": "D",
      "level_number": 1,
      "order_in_level": 1,
      "xp_reward": 120,
      "duration_min": 30,
      "status": "completed",
      "score_composite": 0.88,
      "prerequisites": [],
      "kb_confidence": 0.97
    }
  ],
  "total": 49
}
```

---

### GET /lessons/{lesson_id}
Retorna o conteúdo completo de uma aula.

**Response 200:**
```json
{
  "id": "did-diferenca-diferencas",
  "title": "DiD — Diferença em Diferenças",
  "subtitle": "Inferência causal para campanhas e políticas",
  "module": "B",
  "level_number": 5,
  "xp_reward": 120,
  "duration_min": 30,
  "status": "available",
  "hook_config": { "...": "ver lesson-schema.json" },
  "widget_config": { "...": "ver lesson-schema.json" },
  "kb_content": { "...": "ver lesson-schema.json" },
  "prerequisites": ["a-b-testing", "sql-motor-analise"],
  "connections": ["rdd-regressao-descontinuidade", "bayesian-hierarchical"]
}
```

**Errors:** 404 (não encontrada), 403 (locked — prerequisitos não cumpridos)

---

### POST /lessons/{lesson_id}/start
Marca a aula como iniciada. Cria registro de progresso se não existir.

**Response 200:**
```json
{
  "lesson_id": "did-diferenca-diferencas",
  "status": "in_progress",
  "started_at": "2026-04-18T10:00:00Z"
}
```

---

## EXERCISE ROUTES

### POST /lessons/{lesson_id}/exercise/generate
Gera o exercício personalizado para o aluno. BrainAgent adapta por perfil e histórico.

**Response 200:**
```json
{
  "exercise_id": "uuid",
  "variant": "padrao",
  "context": "Você é analista no PicPay...",
  "question": "Calcule o efeito DiD da campanha...",
  "data": "-- silver.campanha_cofrinho_2024\n-- Tratado | Pré: 4.2...",
  "has_hint": true,
  "xp_if_no_hint": 120,
  "xp_if_hint": 110,
  "rationale": "Score médio 0.84 → variante padrão. Contexto analytics → exemplos Delta Lake."
}
```

---

### POST /lessons/{lesson_id}/exercise/submit
Submete a resposta do aluno para avaliação pelo BrainAgent.

**Request:**
```json
{
  "exercise_id": "uuid",
  "answer": "DiD = (5.8 - 4.2) - (4.6 - 4.1) = 1.6 - 0.5 = 1.1 sessões/semana...",
  "used_hint": false
}
```

**Response 200:**
```json
{
  "scores": {
    "technical": 0.95,
    "methodological": 0.90,
    "antipatterns": 1.0,
    "interpretation": 0.85,
    "composite": 0.92
  },
  "feedback": "O cálculo está correto — DiD de 1.1 sessões/semana...",
  "xp_earned": 120,
  "lesson_completed": true,
  "unlocked_lessons": ["rdd-regressao-descontinuidade"],
  "memory_updated": {
    "episodic": true,
    "procedural": ["Domina cálculo de DiD com SQL"]
  }
}
```

**Errors:** 400 (answer vazia), 404 (exercise_id inválido), 409 (já submetido com sucesso)

---

### GET /lessons/{lesson_id}/exercise/hint
Retorna a dica do exercício. Deduz XP.

**Response 200:**
```json
{
  "hint": "DiD = (Tratado_pós − Tratado_pré) − (Controle_pós − Controle_pré)...",
  "xp_deducted": 10
}
```

---

## PROGRESS ROUTES

### GET /progress/me
Progresso completo do aluno — para a tela de progresso.

**Response 200:**
```json
{
  "by_module": {
    "A": { "total": 13, "completed": 2, "avg_score": 0.85 },
    "B": { "total": 7, "completed": 1, "avg_score": 0.92 },
    "ZERO": { "total": 8, "completed": 8, "avg_score": 0.78 }
  },
  "by_level": [
    { "level": 0, "total": 8, "completed": 8, "unlocked": true },
    { "level": 1, "total": 2, "completed": 1, "unlocked": true },
    { "level": 2, "total": 4, "completed": 0, "unlocked": true }
  ],
  "xp_history": [
    { "date": "2026-04-17", "xp": 220 },
    { "date": "2026-04-18", "xp": 120 }
  ],
  "streak": {
    "current": 3,
    "best": 7,
    "last_activity": "2026-04-18"
  }
}
```

---

## BRAINAGENT ROUTES

### POST /brainagent/chat
Chat livre com o BrainAgent — para dúvidas sobre conceitos da KB.

**Request:**
```json
{
  "message": "Qual a diferença entre RAG e fine-tuning?",
  "context_lesson_id": "rag"
}
```

**Response 200:**
```json
{
  "response": "RAG busca documentos relevantes em tempo real...",
  "relevant_lessons": ["rag", "fine-tuning", "embeddings"],
  "memory_used": {
    "episodic_items": 3,
    "procedural_patterns": 2
  }
}
```

---

### GET /brainagent/recommend
Recomenda a próxima aula com justificativa.

**Response 200:**
```json
{
  "lesson_id": "quando-nao-usar-modelo",
  "title": "Quando NÃO usar modelo — SQL Resolve",
  "reason": "Você concluiu SQL Motor de Análise com score 0.88. Este é o próximo na sequência e desbloqueia Regressão Logística.",
  "alternatives": [
    {
      "lesson_id": "dashboard-html-sql",
      "reason": "Também disponível — complementa SQL com visualização prática"
    }
  ]
}
```

---

### GET /brainagent/memory
Retorna a memória ativa do BrainAgent para o aluno logado.

**Response 200:**
```json
{
  "episodic": [
    {
      "action": "Concluiu SQL Motor de Análise",
      "score": 0.88,
      "created_at": "2026-04-17T18:00:00Z"
    }
  ],
  "procedural": [
    {
      "pattern": "Prefere exemplos com Delta Lake",
      "confidence": 0.85,
      "category": "preference"
    }
  ],
  "semantic": {
    "concepts_mastered": ["sql-motor-analise"],
    "concepts_in_progress": [],
    "confidence_map": {
      "sql-motor-analise": 0.88,
      "delta-lake": 0.0
    }
  },
  "objective": {
    "goal": "Dominar trilha Analytics",
    "progress": 0.04,
    "active": true
  }
}
```

---

## KB ROUTES

### GET /kb/concepts
Lista todos os conceitos da KB com status do aluno.

**Query params:**
- `module` (optional): A, B, C, D, E, ZERO
- `status` (optional): done, progress, gap, locked

**Response 200:**
```json
{
  "concepts": [
    {
      "id": "did-diferenca-diferencas",
      "topic": "DiD — Diferença em Diferenças",
      "module": "B",
      "confidence": 0.92,
      "entropy": 6.1,
      "status": "done",
      "connections": ["rdd-regressao-descontinuidade", "a-b-testing"],
      "lesson_id": "did-diferenca-diferencas"
    }
  ],
  "stats": {
    "total": 49,
    "done": 9,
    "progress": 0,
    "gap": 0,
    "locked": 40
  }
}
```

---

### GET /kb/concepts/{concept_id}
Conteúdo completo de um conceito da KB.

**Response 200:**
```json
{
  "id": "did-diferenca-diferencas",
  "topic": "DiD — Diferença em Diferenças",
  "module": "B",
  "confidence": 0.95,
  "entropy": 6.1,
  "resumo": "Método de inferência causal que estima...",
  "quando_usar": ["Você tem dados antes e depois..."],
  "quando_nao_usar": ["Tendências não são paralelas..."],
  "formula": { "did": "DiD = ...", "regressao": "Y = α + β₁..." },
  "codigo": "WITH base AS (...)",
  "antipatterns": ["Nunca apresentar sem plotar tendências..."],
  "fintech_aplicacao": "PicPay cofrinho: DiD estimou +18%...",
  "connections": ["rdd-regressao-descontinuidade"],
  "student_status": "done",
  "student_score": 0.92
}
```

---

## ERROR RESPONSES

Todos os erros seguem o formato:

```json
{
  "detail": "Mensagem descritiva do erro",
  "error_code": "LESSON_LOCKED",
  "timestamp": "2026-04-18T10:00:00Z"
}
```

**Códigos HTTP usados:**
- `200` OK
- `201` Created
- `400` Bad Request (input inválido)
- `401` Unauthorized (token ausente ou expirado)
- `403` Forbidden (sem permissão — ex: lesson locked)
- `404` Not Found
- `409` Conflict (ex: tentativa de fazer diagnóstico duas vezes)
- `422` Validation Error (Pydantic)
- `429` Too Many Requests (rate limit BrainAgent)
- `500` Internal Server Error

---

## RATE LIMITS

```
BrainAgent calls     20 req/hora por aluno
Diagnostic answers   60 req/hora por aluno
Exercise submits     10 req/hora por aula
Geral                200 req/hora por aluno
```
