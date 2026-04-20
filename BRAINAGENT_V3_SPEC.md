# BrainAgent V3 — Technical Specification

**Version**: 3.0.0  
**Author**: Matheus Felix  
**Status**: Production-ready module  
**File**: `brainagent_v3.py` (single-file, zero mandatory deps beyond stdlib)

---

## 1. Overview

BrainAgent V3 is a self-improving, memory-persistent agent framework designed for
production use across multiple fintech projects. It extends V2 with four major additions:

| Component | V1 | V2 | V3 |
|---|---|---|---|
| Memory | Episodic only | 4-layer hierarchy | 4-layer + compiled truth |
| Pruning | Manual | Shannon entropy | Entropy + Ebbinghaus decay |
| Intent routing | None | None | Tier-0 regex classifier |
| Knowledge model | None | Semantic graph | Compiled truth + append-only timeline |
| Consolidation | None | Feedback loop | Dream Cycle daemon |
| Peer review | Council (external) | Council (external) | Council (embedded) |
| Multi-project | One instance | One instance | AgentRegistry |
| Compliance | None | None | SHA256 AuditTrail |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BrainAgentV3.run(query)                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────▼─────────────────┐
              │       IntentClassifier            │
              │  Tier 0: regex (<1ms, zero LLM)   │
              │  Tier 1: Shannon entropy scoring  │
              │  Tier 2: LLM fallback + log       │
              └────────────────┬─────────────────┘
                               │  ClassificationResult
              ┌────────────────▼─────────────────┐
              │          MemorySystem             │
              │  ┌─────────────────────────────┐ │
              │  │  Working   (deque, 20 items) │ │
              │  │  Episodic  (JSONL + decay)   │ │
              │  │  Semantic  (graph + truth)   │ │
              │  │  Procedural (pattern store)  │ │
              │  └─────────────────────────────┘ │
              └────────────────┬─────────────────┘
                               │  context bundle
              ┌────────────────▼─────────────────┐
              │           LLMAdapter              │
              │  Builds system prompt from memory │
              │  Calls Anthropic API              │
              └────────────────┬─────────────────┘
                               │  draft answer
              ┌────────────────▼─────────────────┐
              │    Council (optional)             │
              │  Architect / Critic / Pragmatist  │
              │  Ethicist / Synthesizer           │
              └────────────────┬─────────────────┘
                               │  final answer
              ┌────────────────▼─────────────────┐
              │    Episode persisted to memory    │
              │    AgentResponse returned         │
              └─────────────────────────────────┘

Background thread:
  DreamCycle ─── every N seconds ──► prune + promote + extract procedures
```

---

## 3. Modules

### 3.1 IntentClassifier

**Purpose**: Route queries to the right memory layer without an LLM call.

**Pipeline**:
1. Lowercase + strip query
2. Run all INTENT_PATTERNS (regex) in parallel → collect matches
3. Compute Shannon entropy over match confidence scores → single confidence float
4. If confidence ≥ 0.72 → use dominant pattern's intent/route (Tier 1)
5. If confidence < 0.72 → flag as UNKNOWN, route to LLM_FALLBACK (Tier 2), log entry

**Outputs**: `ClassificationResult` with intent, route, confidence, entities, temporal_hint, tier.

**Intent taxonomy** (16 intents across 5 domains):

| Domain | Intents |
|---|---|
| Entity | entity_lookup, entity_update, entity_list |
| Temporal | temporal_query, temporal_recent |
| Fintech | fintech_metric, fintech_campaign, fintech_credit, fintech_pix, fintech_fraud, fintech_lgpd |
| Project | project_status, project_task |
| Agent | agent_skill |
| Fallback | general_search, unknown |

**Route taxonomy** (7 routes):

| Route | Triggers |
|---|---|
| memory_read | Entity lookups, project status |
| memory_write | Entity updates |
| memory_list | List queries |
| temporal_filter | Any query with temporal hint |
| metric_query | Fintech metrics, campaigns |
| vector_search | Credit, Pix, fraud, LGPD, agent skills |
| llm_fallback | Low confidence, no pattern match |

**Fail-improve loop**: Every Tier-2 fallback is logged to `_fallback_log`. Export with
`classifier.export_fallback_log("fallback_log.json")` and use to grow regex patterns over time.

---

### 3.2 MemorySystem

**Purpose**: Persistent, multi-layer memory with entropy-based pruning.

#### Layer 1 — Working Memory
- In-memory `deque(maxlen=20)` scoped to current session
- Populated automatically on every `append_episode()`
- Used for hot context injection into LLM system prompt
- No persistence — resets on process restart

#### Layer 2 — Episodic Memory
- File: `{storage_dir}/{project}/episodic.jsonl`
- One JSON object per line; append-only
- Each episode stores: query, answer, intent, route, entities, temporal_hint, valence, importance, entropy_bits, access_count
- **Retrieval**: scored search combining Ebbinghaus decay weight + query overlap + entity match + intent match + temporal match
- **Pruning**: `prune_low_entropy()` removes episodes with `entropy_bits < threshold` (default 1.5 bits). Logged to `entropy_log.jsonl`.

#### Layer 3 — Semantic Memory
- File: `{storage_dir}/{project}/semantic.json`
- Knowledge graph: `concept → SemanticNode`
- Each node has two zones (GBrain pattern):
  - **compiled_truth**: current best understanding (rewritable via `rewrite_truth()`)
  - **timeline**: append-only evidence trail — never edited, only extended
- Confidence score increases with each rewrite (`+0.05`, capped at 1.0)
- Manual injection: `agent.teach(concept, truth)`
- Auto-promotion: DreamCycle promotes high-importance episodes to semantic nodes

#### Layer 4 — Procedural Memory
- File: `{storage_dir}/{project}/procedural.json`
- Stores learned action patterns keyed by intent type
- Tracks success_count, fail_count, avg_feedback → `reliability` score
- Updated by `feedback()` calls
- Retrieved during LLM context building to guide responses

#### Optional — Vector Store (ChromaDB)
- Activated with `use_vector_store=True` (requires `pip install chromadb`)
- Persisted at `{storage_dir}/{project}/chroma/`
- Episodes embedded and stored for semantic similarity search
- Falls back gracefully if ChromaDB unavailable

---

### 3.3 DreamCycle

**Purpose**: Background memory consolidation daemon (executable code, not model-interpreted skills).

**Runs every**: `dream_cycle_interval` seconds (default: 3600)

**Three passes**:
1. `prune_low_entropy()` — remove episodic noise below entropy threshold
2. `_promote_to_semantic()` — create semantic nodes for high-importance episodes with entities
3. `_extract_procedures()` — populate procedural memory from high-valence episodes

**Key distinction from GBrain**: Dream cycle logic is compiled Python, not model-interpreted Markdown. Reliability does not depend on model instruction-following.

**Manual trigger**: `agent.run_dream_cycle()` — returns summary dict with counts.

**Thread**: daemon=True, stops on process exit. Stop explicitly with `agent.dream_cycle.stop()`.

---

### 3.4 Council

**Purpose**: Multi-archetype peer review for high-stakes responses (optional, adds LLM cost).

**Archetypes**:
- **Architect** — structural soundness, long-term design
- **Critic** — weaknesses, blind spots, failure modes
- **Pragmatist** — operational constraints, real-world limits
- **Ethicist** — LGPD, BCB, COAF compliance, fairness, harm
- **Synthesizer** — consolidates all critiques into a final recommendation

**Activation**: `AgentConfig(enable_council=True, council_archetypes=[...])`

**Cost**: Each archetype = 1 LLM call. Default config (3 archetypes) = 3 extra calls per `run()`.

**Use case**: Activate selectively for high-stakes decisions (credit, compliance, campaign design).
For interactive/exploratory queries, keep disabled.

---

### 3.5 LLMAdapter

**Purpose**: Build context-aware system prompt from memory and call Anthropic API.

**System prompt structure** (injected in this order):
1. Agent identity + project name
2. Domain context (`system_context` from config)
3. Compiled knowledge from semantic nodes matching entities
4. Top-4 relevant episodic memories (decay-scored)
5. Best procedural pattern for this intent (if reliability > 0)
6. Last 3 working memory items
7. Classification metadata (intent, route, confidence, entities, temporal hint)

**Fallback**: If `anthropic` not installed, returns a structured mock response with all metadata.
This enables testing the full pipeline without API keys.

---

### 3.6 AgentRegistry

**Purpose**: Manage multiple BrainAgentV3 instances for multi-client deployments.

```python
registry = AgentRegistry()
registry.register("picpay",    AgentConfig(project="picpay", ...))
registry.register("santander", AgentConfig(project="santander", ...))

agent = registry.get("picpay")
resp  = agent.run("Qual o TPV do mês?")

# Broadcast same query to all agents
all_responses = registry.broadcast("Status dos projetos ativos?")

# Health check all
registry.health_all()
```

---

### 3.7 AuditTrail

**Purpose**: Immutable, SHA256-chained log for LGPD/BCB compliance.

- Append-only JSONL at `{storage_dir}/audit.jsonl`
- Each entry: timestamp, event_type, payload, prev_hash, hash
- SHA256 chain links every entry to its predecessor
- `verify_chain()` returns `True` if chain is intact, `False` if tampered
- Use `audit.log("agent_run", {...})` from application layer

---

## 4. Configuration Reference

```python
@dataclass
class AgentConfig:
    project: str = "default"              # Project/client name — isolates storage
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2048
    working_memory_max: int = 20          # Deque size for hot context
    entropy_prune_threshold: float = 1.5  # bits — below this, episode is pruned
    confidence_threshold: float = 0.72    # below this → LLM fallback (Tier 2)
    decay_half_life_days: float = 30.0    # Ebbinghaus half-life for episodic decay
    dream_cycle_interval: int = 3600      # seconds between consolidation passes
    enable_dream_cycle: bool = True       # set False for tests / notebooks
    enable_council: bool = False          # True adds N LLM calls per run()
    council_archetypes: list[str] = [     # which archetypes to activate
        "architect", "critic", "synthesizer"
    ]
    storage_dir: str = ".brainagent"      # root dir for all persistent files
    use_vector_store: bool = False        # requires chromadb
    system_context: str = ""             # extra domain context in system prompt
    agent_identity: str = ""           # if set, replaces default BrainAgent intro (e.g. Academy tutor)
```

---

## 5. Storage Layout

```
.brainagent/
└── {project}/
    ├── episodic.jsonl         ← interaction log (append-only)
    ├── semantic.json          ← compiled truth knowledge graph
    ├── procedural.json        ← learned action patterns
    ├── entropy_log.jsonl      ← pruned episode log
    └── chroma/                ← ChromaDB vector store (optional)
        └── ...
└── audit.jsonl                ← SHA256-chained compliance log
```

---

## 6. Installation

```bash
# Minimal (stdlib only, mock LLM responses)
# No installation needed — just copy brainagent_v3.py

# Full (real LLM responses)
pip install anthropic

# With vector store
pip install anthropic chromadb

# All optional
pip install anthropic chromadb pydantic
```

---

## 7. Usage Examples

### 7.1 Basic

```python
from brainagent_v3 import BrainAgentV3, AgentConfig

cfg   = AgentConfig(project="picpay", system_context="Fintech PJ analytics Brazil")
agent = BrainAgentV3(cfg)

resp = agent.run("Qual o status do nuFormer?")
print(resp.answer)
print(f"Intent: {resp.intent.value}, Confidence: {resp.confidence:.2f}")
```

### 7.2 Feedback loop

```python
resp = agent.run("Analise a campanha do PicPay no Q1 2025")
# User evaluates response quality
agent.feedback(resp.episode_id, score=4.5)
# Procedural memory updated, valence adjusted
```

### 7.3 Manual knowledge injection

```python
agent.teach(
    concept="Onda 6",
    truth="Projeto de newsletter automation para Santander. Pipeline Python/Databricks, 8 semanas.",
    domain="project"
)
node = agent.recall("Onda 6")
print(node.compiled_truth)
print(node.timeline)  # append-only evidence trail
```

### 7.4 Multi-project registry

```python
from brainagent_v3 import AgentRegistry, AgentConfig

registry = AgentRegistry()
for client in ["picpay", "santander", "inter", "c6_bank", "mastercard"]:
    registry.register(client, AgentConfig(
        project=client,
        system_context=f"Fintech analytics for {client}",
        enable_dream_cycle=True,
    ))

# Use specific agent
agent = registry.get("picpay")
resp  = agent.run("Última análise de fraude Pix?")

# Health all
print(registry.health_all())
```

### 7.5 With Council

```python
cfg = AgentConfig(
    project="credit_scoring",
    enable_council=True,
    council_archetypes=["architect", "critic", "ethicist", "synthesizer"],
    system_context="Credit scoring, LGPD compliance, BCB regulatory context"
)
agent = BrainAgentV3(cfg)
resp  = agent.run("Devemos usar dados de Pix como feature no nuFormer?")
# Response synthesized from 4 archetype reviews
print(resp.answer)
```

### 7.6 Audit trail (compliance)

```python
from brainagent_v3 import AuditTrail

audit = AuditTrail(".brainagent/picpay/audit.jsonl")
audit.log("model_decision", {
    "query": "credit_approval",
    "customer_segment": "PJ",
    "model": "nuFormer",
    "decision": "approved",
})
print("Chain valid:", audit.verify_chain())
```

### 7.7 Dream cycle on demand

```python
# Run consolidation manually (e.g., at end of each session)
summary = agent.run_dream_cycle()
print(f"Pruned: {summary['pruned_episodes']}")
print(f"Promoted to semantic: {summary['semantic_promotions']}")
print(f"Procedures extracted: {summary['procedure_extractions']}")
```

### 7.8 Interactive REPL

```bash
python brainagent_v3.py --repl
```

Commands inside REPL:
- `/health` — full health report
- `/dream` — trigger consolidation now
- `/teach PicPay :: Fintech PJ, foco em Pix` — inject compiled truth
- `/recall PicPay` — retrieve semantic node with timeline
- `/quit`

---

## 8. Project Adapter Patterns

### 8.1 nuFormer (credit scoring)

```python
cfg = AgentConfig(
    project="nuformer",
    system_context=(
        "Credit scoring transformer for Brazilian fintech. "
        "AUC target 0.87+. Features: Pix frequency, MCC codes, RFM. "
        "Regulatory: SCR Bacen, LGPD, COAF."
    ),
    enable_council=True,
    council_archetypes=["architect", "ethicist", "synthesizer"],
)
```

### 8.2 Creative Commerce OS

```python
cfg = AgentConfig(
    project="creative_commerce_os",
    system_context=(
        "Fashion AI platform. 6-agent orchestration: catalog, styling, "
        "pricing, campaign, analytics, support. Competing with Fermat.app."
    ),
    enable_dream_cycle=True,
    dream_cycle_interval=1800,  # 30 min — high interaction rate
)
```

### 8.3 SPFC War Room

```python
cfg = AgentConfig(
    project="spfc_war_room",
    system_context=(
        "São Paulo FC football analytics. Pass networks, xG, match modes. "
        "Multi-agent coaching simulator."
    ),
    enable_council=False,    # speed over deliberation
    enable_dream_cycle=True,
    dream_cycle_interval=7200,
)
```

### 8.4 MasterAI Academy

Implementação recomendada: use o módulo **`academy_brainagent.py`** na raiz do repositório MasterAI Academy. Ele define:

- **`ACADEMY_TEACHER_IDENTITY_EN`** — primeira linha do system prompt (tutor sênior, PT-BR por padrão).
- **`ACADEMY_TEACHER_CONTEXT_BASE`** — regras pedagógicas (diagnóstico A→D, não entregar gabarito de exercício de graça, perfis analytics/marketing/etc., tom do CLAUDE.md).
- **`build_academy_teacher_config(student_id, ...)`** — retorna `AgentConfig` com `project="academy_<student_id>"`, **Dream Cycle desligado por padrão** (adequado a FastAPI/workers), **Council desligado por padrão** (economiza chamadas ao Claude).
- **`create_academy_teacher_agent(...)`** — instancia `BrainAgentV3`.
- **`teacher_chat_turn(agent, message, lesson_id=...)`** — um turno de chat com prefixo de contexto de aula opcional.

O arquivo `brainagent_v3.py` aceita **`agent_identity`** opcional em `AgentConfig`: quando preenchido, substitui a intro genérica “You are BrainAgent V3…” no `LLMAdapter`, evitando conflito entre assistente genérico e tutor Academy.

Exemplo manual (equivalente ao helper):

```python
from academy_brainagent import build_academy_teacher_config
from brainagent_v3 import BrainAgentV3

cfg = build_academy_teacher_config(
    student_id="uuid-do-supabase-student",
    profile="analytics",
    lesson_id="did-diferenca-diferencas",
    enable_dream_cycle=False,
    enable_council=False,
)
agent = BrainAgentV3(cfg)
resp = agent.run("Explique quando DiD falha mesmo com tendências paralelas.")
print(resp.answer)
```

Configuração legada (um único projeto compartilhado — menos isolamento por aluno):

```python
cfg = AgentConfig(
    project="masterai_academy",
    system_context=(
        "Corporate AI training platform for Brazilian financial market. "
        "Content: AI strategy, agents, LLM prompting, fintech applications."
    ),
    enable_council=True,
    council_archetypes=["architect", "pragmatist", "synthesizer"],
)
```

---

## 9. V2 → V3 Migration

| V2 component | V3 equivalent | Notes |
|---|---|---|
| `brain_decide_action()` | `agent.run()` | Now includes intent classifier |
| `brain_update_outcome()` | `agent.feedback()` | Same semantic, cleaner API |
| Manual memory writes | `agent.teach()` | Compiled truth model |
| External Council trigger | `enable_council=True` | Embedded, no external script |
| Manual pruning | `run_dream_cycle()` | Automated daemon |
| Single project | `AgentRegistry` | Multi-project out of the box |
| No compliance layer | `AuditTrail` | SHA256 chain, LGPD-ready |

V2 episodic.jsonl files are compatible with V3 — point `storage_dir` to the same path.

---

## 10. Benchmarks & Targets

| Metric | Target | Notes |
|---|---|---|
| Intent classification latency | < 2ms | Tier-0 regex, no LLM |
| Tier-0 hit rate | > 70% | Measure with `get_fallback_log()` |
| Classifier accuracy (labeled set) | > 85% | Run `eval_accuracy()` on sample |
| Episodic search latency | < 50ms | On 1,000 episodes |
| Shannon entropy threshold | 1.5 bits | Tune per project if needed |
| Dream cycle overhead | < 5s per pass | On 500 episodes |
| Audit chain verification | < 1s per 10k entries | |

---

## 11. Known Limitations & Roadmap

**Current limitations**:
- Semantic memory is file-based JSON; for > 10k nodes, migrate to SQLite or Postgres + pgvector
- Vector store (ChromaDB) operates locally; for multi-device use, migrate to Qdrant cloud or Supabase pgvector
- Council adds N LLM calls per run — keep disabled for high-frequency queries
- Classifier patterns are Portuguese-first; English queries may have lower Tier-0 hit rate

**V3.1 roadmap**:
- [ ] Postgres + pgvector backend (drop-in replacement for JSON stores)
- [ ] RRF fusion (vector + keyword) in episodic search — inspired by GBrain PR #64
- [ ] Bidirectional migration (local ↔ cloud storage)
- [ ] Eval harness CLI: `python brainagent_v3.py --eval queries.json`
- [ ] English pattern support in IntentClassifier
- [ ] Streaming response support (Anthropic streaming API)

---

## 12. Dependencies

| Package | Version | Required | Purpose |
|---|---|---|---|
| Python | 3.11+ | ✅ | Core |
| anthropic | >= 0.25 | Optional | Real LLM responses |
| chromadb | >= 0.4 | Optional | Vector store |
| pydantic | >= 2.0 | Optional | Schema validation |

All stdlib imports: `json`, `math`, `re`, `uuid`, `logging`, `threading`, `time`, `hashlib`, `collections`, `dataclasses`, `datetime`, `enum`, `pathlib`, `typing`

---

*BrainAgent V3 — built for fintech, designed to compound.*
