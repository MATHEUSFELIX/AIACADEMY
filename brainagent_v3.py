"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         BRAINAGENT V3                                      ║
║              Self-Improving Agent Framework — Production Grade              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  V1: episodic memory only                                                  ║
║  V2: 4-layer hierarchy + Shannon entropy pruning + closed feedback loop     ║
║  V3: + Intent Classifier (Tier-0 regex) + GBrain-style compiled truth      ║
║      + Dream Cycle daemon + Council peer-review + multi-project adapter    ║
╚══════════════════════════════════════════════════════════════════════════════╝

Author : Matheus Felix
Version: 3.0.0
License: MIT
Requires: Python 3.11+  |  pip install anthropic chromadb pydantic

Quick-start
-----------
    from brainagent_v3 import BrainAgentV3, AgentConfig

    cfg = AgentConfig(project="my_project", model="claude-sonnet-4-20250514")
    agent = BrainAgentV3(cfg)
    response = agent.run("O que sei sobre o cliente PicPay?")
    print(response.answer)
"""

from __future__ import annotations

import json
import math
import re
import uuid
import logging
import threading
import time
import hashlib
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ── Optional heavy deps (graceful degradation) ────────────────────────────────
try:
    import anthropic as _anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

try:
    import chromadb as _chromadb
    _HAS_CHROMA = True
except ImportError:
    _HAS_CHROMA = False

logger = logging.getLogger("brainagent.v3")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ENUMS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

class IntentType(str, Enum):
    ENTITY_LOOKUP    = "entity_lookup"
    ENTITY_UPDATE    = "entity_update"
    ENTITY_LIST      = "entity_list"
    TEMPORAL_QUERY   = "temporal_query"
    TEMPORAL_RECENT  = "temporal_recent"
    FINTECH_METRIC   = "fintech_metric"
    FINTECH_CAMPAIGN = "fintech_campaign"
    FINTECH_CREDIT   = "fintech_credit"
    FINTECH_PIX      = "fintech_pix"
    FINTECH_FRAUD    = "fintech_fraud"
    FINTECH_LGPD     = "fintech_lgpd"
    PROJECT_STATUS   = "project_status"
    PROJECT_TASK     = "project_task"
    AGENT_SKILL      = "agent_skill"
    GENERAL_SEARCH   = "general_search"
    UNKNOWN          = "unknown"


class RouteAction(str, Enum):
    MEMORY_READ      = "memory_read"
    MEMORY_WRITE     = "memory_write"
    MEMORY_LIST      = "memory_list"
    TEMPORAL_FILTER  = "temporal_filter"
    METRIC_QUERY     = "metric_query"
    VECTOR_SEARCH    = "vector_search"
    LLM_FALLBACK     = "llm_fallback"


class MemoryLayer(str, Enum):
    WORKING    = "working"
    EPISODIC   = "episodic"
    SEMANTIC   = "semantic"
    PROCEDURAL = "procedural"


class CouncilArchetype(str, Enum):
    ARCHITECT   = "architect"
    CRITIC      = "critic"
    PRAGMATIST  = "pragmatist"
    ETHICIST    = "ethicist"
    SYNTHESIZER = "synthesizer"


CONFIDENCE_THRESHOLD = 0.72
ENTROPY_PRUNE_THRESHOLD = 1.5   # bits — below this, memory is low-info
DECAY_HALF_LIFE_DAYS  = 30.0
WORKING_MEMORY_MAX    = 20
DREAM_CYCLE_INTERVAL  = 3600    # seconds between dream cycles

INTENT_PATTERNS: list[tuple[str, IntentType, RouteAction, float]] = [
    (r"\b(quem é|o que sei sobre|dossier de|perfil de|ficha de)\b",
        IntentType.ENTITY_LOOKUP,    RouteAction.MEMORY_READ,     0.95),
    (r"\b(atualiza|adiciona|registra|salva|anota)\b.{0,40}\b(sobre|para|de)\b",
        IntentType.ENTITY_UPDATE,    RouteAction.MEMORY_WRITE,    0.92),
    (r"\b(lista|mostre|quais|todos os|todas as)\b.{0,30}\b(clientes|empresas|pessoas|contatos|projetos)\b",
        IntentType.ENTITY_LIST,      RouteAction.MEMORY_LIST,     0.90),
    (r"\b(em \d{4}|no mês de|em (janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)|q[1-4][\s\-]\d{4}|último(s)? (mês|trimestre|ano|semana))\b",
        IntentType.TEMPORAL_QUERY,   RouteAction.TEMPORAL_FILTER, 0.93),
    (r"\b(mais recente|última interação|último contato|recentemente|hoje|ontem|esta semana)\b",
        IntentType.TEMPORAL_RECENT,  RouteAction.TEMPORAL_FILTER, 0.91),
    (r"\b(taxa de aprovação|approval rate|chargeback|tpv|gmv|nrr|arpu|ltv|cac|mau|dau)\b",
        IntentType.FINTECH_METRIC,   RouteAction.METRIC_QUERY,    0.97),
    (r"\b(receita|revenue|margem|volume|transações|ticket médio).{0,30}(picpay|santander|inter|c6|mastercard|banco)\b",
        IntentType.FINTECH_METRIC,   RouteAction.METRIC_QUERY,    0.94),
    (r"\b(campanha|did|diferença em diferenças|lift|efeito causal|ab test|a/b)\b",
        IntentType.FINTECH_CAMPAIGN, RouteAction.METRIC_QUERY,    0.96),
    (r"\b(score de crédito|scoring|nuformer|scr bacen|inadimplência|default|lgd|ead)\b",
        IntentType.FINTECH_CREDIT,   RouteAction.VECTOR_SEARCH,   0.95),
    (r"\b(pix|transferência instantânea|chave pix|dict|spi)\b",
        IntentType.FINTECH_PIX,      RouteAction.VECTOR_SEARCH,   0.97),
    (r"\b(fraude|fraud|anomalia|suspeito|estorno|disputas|contestação)\b",
        IntentType.FINTECH_FRAUD,    RouteAction.VECTOR_SEARCH,   0.96),
    (r"\b(lgpd|bacen|banco central|open finance|resolução bcb|consentimento|dados pessoais)\b",
        IntentType.FINTECH_LGPD,     RouteAction.VECTOR_SEARCH,   0.94),
    (r"\b(status do projeto|onde (eu |nós )?parei|o que (falta|resta)|progresso de|sprint)\b",
        IntentType.PROJECT_STATUS,   RouteAction.MEMORY_READ,     0.91),
    (r"\b(próximo passo|next step|o que fazer|backlog|tarefa|task|pendência)\b",
        IntentType.PROJECT_TASK,     RouteAction.MEMORY_READ,     0.89),
    (r"\b(brainagent|baos|skill|council|shannon entropy|memória do agente|qual ferramenta|qual skill)\b",
        IntentType.AGENT_SKILL,      RouteAction.VECTOR_SEARCH,   0.93),
]

KNOWN_ENTITIES = [
    "picpay","santander","inter","c6 bank","mastercard","bradesco","itaú","nubank","neon","btg","xp",
    "nuformer","baos","brainagent","hubai","masterai","gbrain","onda 6","agentsearch","shopperai",
    "spfc war room","creative commerce os","masterai academy",
]

TEMPORAL_PATTERNS = [
    r"\b(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b",
    r"\b(q[1-4][\s\-]?\d{4})\b",
    r"\b(\d{4}[-/]\d{2})\b",
    r"\b(último(s)? (mês|trimestre|ano|semana|dia)s?)\b",
    r"\b(hoje|ontem|esta semana|este mês|este ano)\b",
]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentConfig:
    """All tunable parameters for a BrainAgent V3 instance."""
    project: str                          = "default"
    model: str                            = "claude-sonnet-4-20250514"
    max_tokens: int                       = 2048
    working_memory_max: int               = WORKING_MEMORY_MAX
    entropy_prune_threshold: float        = ENTROPY_PRUNE_THRESHOLD
    confidence_threshold: float           = CONFIDENCE_THRESHOLD
    decay_half_life_days: float           = DECAY_HALF_LIFE_DAYS
    dream_cycle_interval: int             = DREAM_CYCLE_INTERVAL
    enable_dream_cycle: bool              = True
    enable_council: bool                  = False
    council_archetypes: list[str]         = field(default_factory=lambda: [
        CouncilArchetype.ARCHITECT.value,
        CouncilArchetype.CRITIC.value,
        CouncilArchetype.SYNTHESIZER.value,
    ])
    storage_dir: str                      = ".brainagent"
    use_vector_store: bool                = False   # requires chromadb
    system_context: str                   = ""      # extra domain context
    # If non-empty, replaces the default BrainAgent intro line in LLMAdapter (e.g. MasterAI Academy teacher)
    agent_identity: str                   = ""


@dataclass
class ClassificationResult:
    intent: IntentType
    route: RouteAction
    confidence: float
    entities: list[str]
    temporal_hint: Optional[str]
    raw_query: str
    matched_pattern: Optional[str]
    tier: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["intent"]  = self.intent.value
        d["route"]   = self.route.value
        return d


@dataclass
class Episode:
    """Single interaction stored in episodic memory."""
    id: str               = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str        = field(default_factory=lambda: datetime.utcnow().isoformat())
    project: str          = "default"
    layer: str            = MemoryLayer.EPISODIC.value
    query: str            = ""
    answer: str           = ""
    intent: str           = ""
    route: str            = ""
    entities: list[str]   = field(default_factory=list)
    temporal_hint: Optional[str] = None
    valence: float        = 0.0       # -1 to +1
    importance: float     = 0.5
    feedback_score: Optional[float] = None
    access_count: int     = 0
    entropy_bits: float   = 0.0
    tags: list[str]       = field(default_factory=list)

    def decay_weight(self, half_life_days: float = DECAY_HALF_LIFE_DAYS) -> float:
        age_days = (datetime.utcnow() - datetime.fromisoformat(self.timestamp)).total_seconds() / 86400
        reinforcement = math.log1p(self.access_count) * 0.3
        return self.importance * math.exp(-age_days / half_life_days) + reinforcement

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SemanticNode:
    """Node in the semantic knowledge graph (compiled truth)."""
    id: str               = field(default_factory=lambda: str(uuid.uuid4())[:8])
    concept: str          = ""
    compiled_truth: str   = ""        # best current understanding (rewritable)
    timeline: list[dict]  = field(default_factory=list)  # append-only evidence
    confidence: float     = 0.5
    domain: str           = "general"
    connections: list[str]= field(default_factory=list)
    source_episodes: list[str] = field(default_factory=list)
    last_updated: str     = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_evidence(self, evidence: str, source_id: str = "") -> None:
        """Append-only timeline update (GBrain pattern)."""
        self.timeline.append({
            "ts": datetime.utcnow().isoformat(),
            "evidence": evidence,
            "source": source_id,
        })
        self.last_updated = datetime.utcnow().isoformat()

    def rewrite_truth(self, new_truth: str) -> None:
        """Rewrite compiled truth when evidence changes the picture."""
        old = self.compiled_truth
        self.compiled_truth = new_truth
        self.add_evidence(f"[rewrite] prev='{old[:80]}...'")
        self.confidence = min(1.0, self.confidence + 0.05)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProceduralPattern:
    """A learned action pattern stored in procedural memory."""
    id: str               = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trigger: str          = ""
    action_template: str  = ""
    success_count: int    = 0
    fail_count: int       = 0
    avg_feedback: float   = 0.0
    domain: str           = "general"
    last_used: str        = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def reliability(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5
        return self.success_count / total

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentResponse:
    answer: str
    intent: IntentType
    route: RouteAction
    confidence: float
    entities: list[str]
    temporal_hint: Optional[str]
    memory_hits: list[str]        # episode IDs retrieved
    council_used: bool
    dream_cycle_ran: bool
    tier: int
    episode_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — INTENT CLASSIFIER (Tier-0 regex + Shannon entropy)
# ══════════════════════════════════════════════════════════════════════════════

class IntentClassifier:
    """
    Zero-latency regex-first intent classifier.
    Tier 0: regex (deterministic, <1ms)
    Tier 1: Shannon entropy confidence scoring
    Tier 2: LLM fallback (logged for fail-improve)
    """

    def __init__(self, threshold: float = CONFIDENCE_THRESHOLD):
        self.threshold = threshold
        self._fallback_log: list[dict] = []

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _shannon_confidence(scores: list[float]) -> float:
        if not scores:
            return 0.0
        total = sum(scores)
        if total == 0:
            return 0.0
        probs = [s / total for s in scores]
        H = -sum(p * math.log2(p) for p in probs if p > 0)
        H_max = math.log2(len(scores)) if len(scores) > 1 else 1.0
        norm_entropy = H / H_max if H_max > 0 else 0.0
        dominant = max(scores)
        return round(dominant * (0.6 + 0.4 * (1.0 - norm_entropy)), 4)

    @staticmethod
    def _extract_entities(query: str) -> list[str]:
        q = query.lower()
        return [e for e in KNOWN_ENTITIES if e in q]

    @staticmethod
    def _extract_temporal(query: str) -> Optional[str]:
        q = query.lower()
        for pattern in TEMPORAL_PATTERNS:
            m = re.search(pattern, q)
            if m:
                return m.group(0)
        return None

    def _log_fallback(self, query: str, reason: str) -> None:
        entry = {"query": query, "reason": reason, "ts": datetime.utcnow().isoformat()}
        self._fallback_log.append(entry)
        logger.warning(f"[Classifier] FALLBACK: {entry}")

    # ── public ────────────────────────────────────────────────────────────────

    def classify(self, query: str) -> ClassificationResult:
        q = query.lower().strip()
        entities = self._extract_entities(q)
        temporal = self._extract_temporal(q)

        matches: list[tuple[IntentType, RouteAction, float, str]] = []
        for pattern_str, intent, route, base_conf in INTENT_PATTERNS:
            if re.search(pattern_str, q):
                matches.append((intent, route, base_conf, pattern_str))

        if not matches:
            self._log_fallback(q, "no_pattern_match")
            return ClassificationResult(
                intent=IntentType.UNKNOWN, route=RouteAction.LLM_FALLBACK,
                confidence=0.0, entities=entities, temporal_hint=temporal,
                raw_query=query, matched_pattern=None, tier=2,
            )

        scores = [m[2] for m in matches]
        confidence = self._shannon_confidence(scores)
        dominant   = max(matches, key=lambda x: x[2])
        best_intent, best_route, _, best_pattern = dominant

        if temporal and best_intent not in (IntentType.TEMPORAL_QUERY, IntentType.TEMPORAL_RECENT):
            best_route = RouteAction.TEMPORAL_FILTER

        tier = 1
        if confidence < self.threshold:
            self._log_fallback(q, f"low_confidence:{confidence:.3f}")
            best_intent = IntentType.UNKNOWN
            best_route  = RouteAction.LLM_FALLBACK
            tier = 2

        return ClassificationResult(
            intent=best_intent, route=best_route, confidence=confidence,
            entities=entities, temporal_hint=temporal, raw_query=query,
            matched_pattern=best_pattern, tier=tier,
        )

    def get_fallback_log(self) -> list[dict]:
        return list(self._fallback_log)

    def export_fallback_log(self, path: str = "fallback_log.json") -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._fallback_log, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — MEMORY SYSTEM (4 layers)
# ══════════════════════════════════════════════════════════════════════════════

class MemorySystem:
    """
    Hierarchical 4-layer memory:
      Working    → deque (hot context, current session)
      Episodic   → JSONL per-project (interaction log, Ebbinghaus decay)
      Semantic   → JSON graph (compiled truth + append-only timeline)
      Procedural → JSON list (learned action patterns)
    """

    def __init__(self, config: AgentConfig):
        self.config   = config
        self.base_dir = Path(config.storage_dir) / config.project
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Working memory
        self._working: deque[dict] = deque(maxlen=config.working_memory_max)

        # File paths
        self._episodic_path   = self.base_dir / "episodic.jsonl"
        self._semantic_path   = self.base_dir / "semantic.json"
        self._procedural_path = self.base_dir / "procedural.json"
        self._entropy_log     = self.base_dir / "entropy_log.jsonl"

        # Load persistent stores
        self._semantic: dict[str, SemanticNode]     = self._load_semantic()
        self._procedural: list[ProceduralPattern]   = self._load_procedural()

        # Optional ChromaDB
        self._vector_collection = None
        if config.use_vector_store and _HAS_CHROMA:
            self._init_vector_store()

    # ── persistence ───────────────────────────────────────────────────────────

    def _load_semantic(self) -> dict[str, SemanticNode]:
        if not self._semantic_path.exists():
            return {}
        raw = json.loads(self._semantic_path.read_text(encoding="utf-8"))
        return {k: SemanticNode(**v) for k, v in raw.items()}

    def _save_semantic(self) -> None:
        data = {k: v.to_dict() for k, v in self._semantic.items()}
        self._semantic_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_procedural(self) -> list[ProceduralPattern]:
        if not self._procedural_path.exists():
            return []
        raw = json.loads(self._procedural_path.read_text(encoding="utf-8"))
        return [ProceduralPattern(**p) for p in raw]

    def _save_procedural(self) -> None:
        self._procedural_path.write_text(
            json.dumps([p.to_dict() for p in self._procedural], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _init_vector_store(self) -> None:
        client = _chromadb.PersistentClient(path=str(self.base_dir / "chroma"))
        self._vector_collection = client.get_or_create_collection(
            f"brain_{self.config.project}"
        )

    # ── working memory ────────────────────────────────────────────────────────

    def push_working(self, item: dict) -> None:
        self._working.appendleft(item)

    def get_working_context(self, n: int = 5) -> list[dict]:
        return list(self._working)[:n]

    # ── episodic memory ───────────────────────────────────────────────────────

    def append_episode(self, ep: Episode) -> None:
        ep.entropy_bits = self._compute_entropy(ep.answer)
        with open(self._episodic_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ep.to_dict(), ensure_ascii=False) + "\n")
        self.push_working({"type": "episode", "id": ep.id, "query": ep.query, "answer": ep.answer[:200]})

        if self._vector_collection and _HAS_CHROMA:
            self._vector_collection.add(
                documents=[ep.query + " " + ep.answer],
                metadatas=[{"project": ep.project, "intent": ep.intent, "id": ep.id}],
                ids=[ep.id],
            )

    def load_episodes(self, n: int = 100) -> list[Episode]:
        if not self._episodic_path.exists():
            return []
        lines = self._episodic_path.read_text(encoding="utf-8").strip().split("\n")
        episodes = []
        for line in lines[-n:]:
            try:
                episodes.append(Episode(**json.loads(line)))
            except Exception:
                pass
        return episodes

    def search_episodes(
        self,
        query: str = "",
        intent: Optional[str] = None,
        entities: Optional[list[str]] = None,
        temporal_hint: Optional[str] = None,
        n: int = 5,
    ) -> list[Episode]:
        episodes = self.load_episodes(200)
        now = datetime.utcnow()
        scored: list[tuple[float, Episode]] = []

        for ep in episodes:
            score = ep.decay_weight(self.config.decay_half_life_days)
            if query and (query.lower() in ep.query.lower() or query.lower() in ep.answer.lower()):
                score += 0.4
            if intent and ep.intent == intent:
                score += 0.2
            if entities:
                overlap = len(set(entities) & set(ep.entities))
                score += overlap * 0.15
            if temporal_hint and ep.temporal_hint == temporal_hint:
                score += 0.25
            scored.append((score, ep))

        scored.sort(key=lambda x: -x[0])
        return [ep for _, ep in scored[:n]]

    def prune_low_entropy(self) -> int:
        """Remove episodic entries with entropy below threshold (Shannon pruning)."""
        if not self._episodic_path.exists():
            return 0
        episodes = self.load_episodes(1000)
        kept, pruned = [], []
        for ep in episodes:
            if ep.entropy_bits >= self.config.entropy_prune_threshold:
                kept.append(ep)
            else:
                pruned.append(ep)
                self._log_entropy_prune(ep)

        # Rewrite file
        self._episodic_path.write_text(
            "\n".join(json.dumps(ep.to_dict(), ensure_ascii=False) for ep in kept) + "\n",
            encoding="utf-8",
        )
        logger.info(f"[Prune] Kept {len(kept)}, pruned {len(pruned)} low-entropy episodes.")
        return len(pruned)

    def _log_entropy_prune(self, ep: Episode) -> None:
        entry = {
            "id": ep.id, "ts": datetime.utcnow().isoformat(),
            "entropy_bits": ep.entropy_bits, "query": ep.query[:80],
        }
        with open(self._entropy_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    # ── semantic memory ───────────────────────────────────────────────────────

    def upsert_semantic(self, concept: str, truth: str, domain: str = "general",
                        source_id: str = "", connections: Optional[list[str]] = None) -> SemanticNode:
        key = concept.lower().replace(" ", "_")
        if key in self._semantic:
            node = self._semantic[key]
            node.rewrite_truth(truth)
        else:
            node = SemanticNode(
                concept=concept, compiled_truth=truth, domain=domain,
                connections=connections or [],
                source_episodes=[source_id] if source_id else [],
            )
            node.add_evidence(f"Initial capture: '{truth[:80]}'", source_id)
            self._semantic[key] = node

        self._save_semantic()
        return node

    def get_semantic(self, concept: str) -> Optional[SemanticNode]:
        key = concept.lower().replace(" ", "_")
        return self._semantic.get(key)

    def search_semantic(self, entities: list[str]) -> list[SemanticNode]:
        results = []
        for e in entities:
            node = self.get_semantic(e)
            if node:
                results.append(node)
        return results

    # ── procedural memory ─────────────────────────────────────────────────────

    def update_procedural(self, trigger: str, action: str, success: bool,
                          feedback: float = 0.0, domain: str = "general") -> None:
        for p in self._procedural:
            if p.trigger == trigger:
                if success:
                    p.success_count += 1
                else:
                    p.fail_count += 1
                p.avg_feedback = (p.avg_feedback + feedback) / 2
                p.last_used = datetime.utcnow().isoformat()
                self._save_procedural()
                return

        self._procedural.append(ProceduralPattern(
            trigger=trigger, action_template=action,
            success_count=1 if success else 0,
            fail_count=0 if success else 1,
            avg_feedback=feedback, domain=domain,
        ))
        self._save_procedural()

    def get_best_procedure(self, trigger: str) -> Optional[ProceduralPattern]:
        candidates = [p for p in self._procedural if p.trigger == trigger]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.reliability)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_entropy(text: str) -> float:
        """Shannon entropy of character distribution in bits."""
        if not text:
            return 0.0
        freq: dict[str, int] = {}
        for c in text:
            freq[c] = freq.get(c, 0) + 1
        n = len(text)
        return -sum((c / n) * math.log2(c / n) for c in freq.values())

    def health_report(self) -> dict:
        episodes = self.load_episodes(1000)
        low_entropy = [e for e in episodes if e.entropy_bits < self.config.entropy_prune_threshold]
        return {
            "project": self.config.project,
            "episodic_total": len(episodes),
            "low_entropy_episodes": len(low_entropy),
            "semantic_nodes": len(self._semantic),
            "procedural_patterns": len(self._procedural),
            "working_memory_size": len(self._working),
            "vector_store": self._vector_collection is not None,
        }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — DREAM CYCLE (background consolidation)
# ══════════════════════════════════════════════════════════════════════════════

class DreamCycle:
    """
    Background daemon that runs memory consolidation:
    1. Prune low-entropy episodes
    2. Promote high-importance episodes to semantic memory
    3. Extract procedural patterns from high-valence episodes
    4. Rewrite stale compiled truths

    Runs in a daemon thread; can also be triggered manually.
    """

    def __init__(self, memory: MemorySystem, config: AgentConfig):
        self.memory  = memory
        self.config  = config
        self._thread: Optional[threading.Thread] = None
        self._stop   = threading.Event()
        self._last_run: Optional[datetime] = None

    def run_once(self) -> dict:
        """Execute one consolidation pass. Returns summary dict."""
        start = datetime.utcnow()
        pruned   = self.memory.prune_low_entropy()
        promoted = self._promote_to_semantic()
        patterns = self._extract_procedures()
        self._last_run = datetime.utcnow()
        elapsed = (datetime.utcnow() - start).total_seconds()

        summary = {
            "ts": start.isoformat(),
            "pruned_episodes": pruned,
            "semantic_promotions": promoted,
            "procedure_extractions": patterns,
            "elapsed_s": round(elapsed, 3),
        }
        logger.info(f"[DreamCycle] {summary}")
        return summary

    def _promote_to_semantic(self) -> int:
        episodes = self.memory.load_episodes(200)
        promoted = 0
        for ep in episodes:
            if ep.importance >= 0.8 and ep.entities:
                for entity in ep.entities:
                    existing = self.memory.get_semantic(entity)
                    if not existing:
                        truth = f"Entity '{entity}' mentioned in context: {ep.query[:120]}"
                        self.memory.upsert_semantic(
                            concept=entity, truth=truth,
                            domain="entity", source_id=ep.id,
                        )
                        promoted += 1
        return promoted

    def _extract_procedures(self) -> int:
        episodes = self.memory.load_episodes(200)
        extracted = 0
        for ep in episodes:
            if ep.valence >= 0.7 and ep.intent:
                best = self.memory.get_best_procedure(ep.intent)
                if not best or best.reliability < 0.8:
                    self.memory.update_procedural(
                        trigger=ep.intent,
                        action=ep.answer[:200],
                        success=True,
                        feedback=ep.valence,
                    )
                    extracted += 1
        return extracted

    def start(self) -> None:
        if not self.config.enable_dream_cycle:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DreamCycle")
        self._thread.start()
        logger.info("[DreamCycle] Daemon started.")

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self.config.dream_cycle_interval)
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"[DreamCycle] Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — COUNCIL PEER REVIEW (multi-archetype critique)
# ══════════════════════════════════════════════════════════════════════════════

COUNCIL_SYSTEM_PROMPTS: dict[str, str] = {
    CouncilArchetype.ARCHITECT.value: (
        "You are the Architect archetype in a peer-review council. "
        "Your role: evaluate the structural soundness and long-term design implications "
        "of a proposed answer or action. Be rigorous, systemic, and forward-looking. "
        "Respond in 2-3 concise sentences."
    ),
    CouncilArchetype.CRITIC.value: (
        "You are the Critic archetype. Find weaknesses, blind spots, unstated assumptions, "
        "and potential failure modes in the proposed answer. Be direct and specific. "
        "Respond in 2-3 concise sentences."
    ),
    CouncilArchetype.PRAGMATIST.value: (
        "You are the Pragmatist. Focus on what is immediately actionable, "
        "what can go wrong in practice, and what the real-world constraints are. "
        "Ground every critique in operational reality. Respond in 2-3 sentences."
    ),
    CouncilArchetype.ETHICIST.value: (
        "You are the Ethicist. Evaluate for regulatory compliance (LGPD, BCB, COAF), "
        "fairness, transparency, and potential for harm. Flag anything that should not "
        "proceed without further review. Respond in 2-3 sentences."
    ),
    CouncilArchetype.SYNTHESIZER.value: (
        "You are the Synthesizer. Given the critiques from other archetypes, produce a "
        "single consolidated recommendation that integrates the strongest points. "
        "Be decisive and concrete. Respond in 3-4 sentences."
    ),
}


class Council:
    """
    Multi-archetype peer-review layer.
    Given a draft answer, runs each selected archetype and synthesizes.
    Requires Anthropic client.
    """

    def __init__(self, client: Any, config: AgentConfig):
        self.client   = client
        self.config   = config
        self.archetypes = config.council_archetypes

    def review(self, question: str, draft_answer: str) -> dict:
        if not _HAS_ANTHROPIC:
            return {"error": "anthropic not installed", "synthesis": draft_answer}

        reviews: dict[str, str] = {}
        prompt = f"Question: {question}\n\nDraft answer:\n{draft_answer}"

        for archetype in self.archetypes:
            if archetype == CouncilArchetype.SYNTHESIZER.value:
                continue  # run synthesizer last
            sys_prompt = COUNCIL_SYSTEM_PROMPTS.get(archetype, "Review this answer briefly.")
            try:
                resp = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=256,
                    system=sys_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                reviews[archetype] = resp.content[0].text
            except Exception as e:
                reviews[archetype] = f"[error: {e}]"

        # Synthesizer pass
        if CouncilArchetype.SYNTHESIZER.value in self.archetypes:
            critique_block = "\n".join(f"[{k}]: {v}" for k, v in reviews.items())
            synth_prompt = (
                f"{prompt}\n\nPeer critique:\n{critique_block}"
            )
            try:
                resp = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=512,
                    system=COUNCIL_SYSTEM_PROMPTS[CouncilArchetype.SYNTHESIZER.value],
                    messages=[{"role": "user", "content": synth_prompt}],
                )
                reviews[CouncilArchetype.SYNTHESIZER.value] = resp.content[0].text
            except Exception as e:
                reviews[CouncilArchetype.SYNTHESIZER.value] = draft_answer

        return reviews


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — LLM ADAPTER
# ══════════════════════════════════════════════════════════════════════════════

class LLMAdapter:
    """
    Thin wrapper around the Anthropic client.
    Builds context-aware system prompt from memory layers.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self._client = None
        if _HAS_ANTHROPIC:
            self._client = _anthropic.Anthropic()

    def generate(
        self,
        query: str,
        classification: ClassificationResult,
        memory: MemorySystem,
    ) -> str:
        """
        Build context from memory + classification and call LLM.
        Falls back to a structured mock if Anthropic not available.
        """
        # Retrieve relevant context
        episodes  = memory.search_episodes(
            query=query,
            intent=classification.intent.value,
            entities=classification.entities,
            temporal_hint=classification.temporal_hint,
            n=4,
        )
        sem_nodes = memory.search_semantic(classification.entities)
        procedure = memory.get_best_procedure(classification.intent.value)
        working   = memory.get_working_context(3)

        # Build system prompt
        default_intro = (
            "You are BrainAgent V3, a context-aware AI assistant with persistent memory."
        )
        intro = (
            self.config.agent_identity.strip()
            if getattr(self.config, "agent_identity", "").strip()
            else default_intro
        )
        system_parts = [
            intro,
            f"Project: {self.config.project}",
        ]
        if self.config.system_context:
            system_parts.append(f"Domain context: {self.config.system_context}")
        if sem_nodes:
            truths = "\n".join(f"- [{n.concept}]: {n.compiled_truth}" for n in sem_nodes)
            system_parts.append(f"\nCompiled knowledge:\n{truths}")
        if episodes:
            ep_block = "\n".join(
                f"- [{ep.timestamp[:10]}] Q: {ep.query[:80]} A: {ep.answer[:120]}"
                for ep in episodes
            )
            system_parts.append(f"\nRelevant past interactions:\n{ep_block}")
        if procedure:
            system_parts.append(
                f"\nBest known procedure for '{classification.intent.value}' "
                f"(reliability {procedure.reliability:.2f}):\n{procedure.action_template[:200]}"
            )
        if working:
            wk = "\n".join(f"- {w.get('query','')[:60]}" for w in working)
            system_parts.append(f"\nRecent working context:\n{wk}")

        system_parts.append(
            f"\nIntent: {classification.intent.value} | Route: {classification.route.value} "
            f"| Confidence: {classification.confidence:.2f}"
        )
        if classification.entities:
            system_parts.append(f"Key entities: {', '.join(classification.entities)}")
        if classification.temporal_hint:
            system_parts.append(f"Temporal focus: {classification.temporal_hint}")

        system_prompt = "\n".join(system_parts)

        if not self._client:
            return (
                f"[BrainAgent V3 — mock response]\n"
                f"Query: {query}\n"
                f"Intent: {classification.intent.value} | Route: {classification.route.value}\n"
                f"Entities: {classification.entities}\n"
                f"Memory hits: {len(episodes)} episodes, {len(sem_nodes)} semantic nodes.\n"
                f"Install `anthropic` for real LLM responses."
            )

        resp = self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": query}],
        )
        return resp.content[0].text


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — BRAINAGENT V3 (main orchestrator)
# ══════════════════════════════════════════════════════════════════════════════

class BrainAgentV3:
    """
    BrainAgent V3 — main entry point.

    Usage
    -----
    cfg   = AgentConfig(project="picpay", system_context="Fintech PJ analytics")
    agent = BrainAgentV3(cfg)

    # Single-turn
    resp = agent.run("Qual o status do nuFormer?")
    print(resp.answer)

    # Multi-turn with feedback
    resp = agent.run("Analise de fraude Q3")
    agent.feedback(resp.episode_id, score=4.5)

    # Manual dream cycle
    agent.dream_cycle.run_once()

    # Switch project (multi-project support)
    agent.switch_project("santander")
    """

    VERSION = "3.0.0"

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config      = config or AgentConfig()
        self.classifier  = IntentClassifier(self.config.confidence_threshold)
        self.memory      = MemorySystem(self.config)
        self.llm         = LLMAdapter(self.config)
        self.dream_cycle = DreamCycle(self.memory, self.config)
        self._council: Optional[Council] = None

        if self.config.enable_council and _HAS_ANTHROPIC:
            client = _anthropic.Anthropic() if _HAS_ANTHROPIC else None
            if client:
                self._council = Council(client, self.config)

        if self.config.enable_dream_cycle:
            self.dream_cycle.start()

        logger.info(f"[BrainAgent V3] Initialized. Project={self.config.project}")

    # ── main run ──────────────────────────────────────────────────────────────

    def run(self, query: str) -> AgentResponse:
        """
        Full inference pipeline:
        1. Classify intent (Tier-0 regex → Shannon entropy → LLM fallback)
        2. Retrieve memory (episodic + semantic + procedural + working)
        3. Generate answer (LLM with context)
        4. Optionally run Council peer review
        5. Persist episode to memory
        6. Return AgentResponse
        """
        # Step 1: Classify
        clf = self.classifier.classify(query)

        # Step 2+3: Generate
        answer = self.llm.generate(query, clf, self.memory)

        # Step 4: Council
        council_used  = False
        council_synth = answer
        if self._council and self.config.enable_council:
            reviews      = self._council.review(query, answer)
            synth_key    = CouncilArchetype.SYNTHESIZER.value
            council_synth = reviews.get(synth_key, answer)
            council_used  = True
            answer        = council_synth

        # Step 5: Persist
        episodes_retrieved = self.memory.search_episodes(
            query=query, intent=clf.intent.value,
            entities=clf.entities, n=4,
        )
        ep = Episode(
            project=self.config.project,
            query=query,
            answer=answer,
            intent=clf.intent.value,
            route=clf.route.value,
            entities=clf.entities,
            temporal_hint=clf.temporal_hint,
            importance=self._score_importance(clf),
        )
        self.memory.append_episode(ep)

        return AgentResponse(
            answer=answer,
            intent=clf.intent,
            route=clf.route,
            confidence=clf.confidence,
            entities=clf.entities,
            temporal_hint=clf.temporal_hint,
            memory_hits=[e.id for e in episodes_retrieved],
            council_used=council_used,
            dream_cycle_ran=False,
            tier=clf.tier,
            episode_id=ep.id,
        )

    # ── feedback loop ─────────────────────────────────────────────────────────

    def feedback(self, episode_id: str, score: float, notes: str = "") -> None:
        """
        Record user feedback (1-5) for an episode.
        Updates procedural memory and episode valence.
        """
        if not (1.0 <= score <= 5.0):
            raise ValueError("Score must be in [1, 5].")
        normalized = (score - 1) / 4      # → [0, 1]
        valence    = normalized * 2 - 1   # → [-1, 1]
        success    = score >= 3.5

        episodes = self.memory.load_episodes(500)
        for ep in episodes:
            if ep.id == episode_id:
                ep.feedback_score = score
                ep.valence        = valence
                ep.importance     = min(1.0, ep.importance + 0.1 * normalized)
                self.memory.update_procedural(
                    trigger=ep.intent, action=ep.answer[:200],
                    success=success, feedback=normalized,
                )
                logger.info(f"[Feedback] Episode {episode_id}: score={score}, valence={valence:.2f}")
                break

    # ── multi-project support ─────────────────────────────────────────────────

    def switch_project(self, project: str) -> None:
        """Hot-swap project context without restarting the agent."""
        self.config.project  = project
        self.memory          = MemorySystem(self.config)
        self.dream_cycle     = DreamCycle(self.memory, self.config)
        if self.config.enable_dream_cycle:
            self.dream_cycle.start()
        logger.info(f"[BrainAgent V3] Switched to project: {project}")

    # ── semantic knowledge API ────────────────────────────────────────────────

    def teach(self, concept: str, truth: str, domain: str = "general") -> SemanticNode:
        """Manually inject a compiled truth into semantic memory."""
        return self.memory.upsert_semantic(concept=concept, truth=truth, domain=domain)

    def recall(self, concept: str) -> Optional[SemanticNode]:
        """Retrieve a semantic node by concept name."""
        return self.memory.get_semantic(concept)

    # ── diagnostics ───────────────────────────────────────────────────────────

    def health(self) -> dict:
        report = self.memory.health_report()
        report["version"] = self.VERSION
        report["model"] = self.config.model
        report["dream_cycle_active"] = (
            self.dream_cycle._thread is not None and
            self.dream_cycle._thread.is_alive()
            if self.dream_cycle._thread else False
        )
        report["council_enabled"] = self._council is not None
        report["classifier_fallbacks"] = len(self.classifier.get_fallback_log())
        return report

    def run_dream_cycle(self) -> dict:
        """Manually trigger a dream cycle consolidation pass."""
        return self.dream_cycle.run_once()

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _score_importance(clf: ClassificationResult) -> float:
        base = 0.5
        if clf.confidence > 0.9:
            base += 0.2
        if clf.entities:
            base += min(0.15, len(clf.entities) * 0.05)
        if clf.temporal_hint:
            base += 0.05
        return min(1.0, base)

    def __repr__(self) -> str:
        return f"BrainAgentV3(project={self.config.project!r}, model={self.config.model!r})"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — MULTI-PROJECT REGISTRY (manage multiple agent instances)
# ══════════════════════════════════════════════════════════════════════════════

class AgentRegistry:
    """
    Manage multiple BrainAgentV3 instances (one per project/client).
    Used when running agents for PicPay + Santander + Inter simultaneously.

    Usage
    -----
    registry = AgentRegistry()
    registry.register("picpay", AgentConfig(project="picpay", ...))
    registry.register("santander", AgentConfig(project="santander", ...))

    agent = registry.get("picpay")
    resp  = agent.run("Qual o TPV do mês?")
    """

    def __init__(self):
        self._agents: dict[str, BrainAgentV3] = {}

    def register(self, name: str, config: AgentConfig) -> BrainAgentV3:
        agent = BrainAgentV3(config)
        self._agents[name] = agent
        logger.info(f"[Registry] Registered agent: {name}")
        return agent

    def get(self, name: str) -> BrainAgentV3:
        if name not in self._agents:
            raise KeyError(f"No agent registered as '{name}'.")
        return self._agents[name]

    def list_projects(self) -> list[str]:
        return list(self._agents.keys())

    def broadcast(self, query: str) -> dict[str, AgentResponse]:
        """Run the same query against all registered agents."""
        return {name: agent.run(query) for name, agent in self._agents.items()}

    def health_all(self) -> dict[str, dict]:
        return {name: agent.health() for name, agent in self._agents.items()}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — AUDIT TRAIL (immutable SHA256-signed log)
# ══════════════════════════════════════════════════════════════════════════════

class AuditTrail:
    """
    Append-only audit log with SHA256 chain for tamper detection.
    Required for fintech/LGPD compliance contexts.
    """

    def __init__(self, path: str = ".brainagent/audit.jsonl"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self._path.exists():
            return "genesis"
        lines = self._path.read_text(encoding="utf-8").strip().split("\n")
        for line in reversed(lines):
            try:
                return json.loads(line).get("hash", "genesis")
            except Exception:
                pass
        return "genesis"

    def log(self, event_type: str, payload: dict, agent_version: str = "3.0.0") -> str:
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "event": event_type,
            "agent_version": agent_version,
            "payload": payload,
            "prev_hash": self._prev_hash,
        }
        entry_str = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        h = hashlib.sha256(entry_str.encode()).hexdigest()
        entry["hash"] = h
        self._prev_hash = h
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return h

    def verify_chain(self) -> bool:
        if not self._path.exists():
            return True
        lines = self._path.read_text(encoding="utf-8").strip().split("\n")
        prev = "genesis"
        for line in lines:
            try:
                entry = json.loads(line)
                stored_hash = entry.pop("hash", None)
                entry_str = json.dumps(entry, ensure_ascii=False, sort_keys=True)
                computed = hashlib.sha256(entry_str.encode()).hexdigest()
                if computed != stored_hash:
                    return False
                if entry.get("prev_hash") != prev:
                    return False
                prev = stored_hash
            except Exception:
                return False
        return True


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — CLI / REPL (optional interactive mode)
# ══════════════════════════════════════════════════════════════════════════════

def repl(project: str = "default", model: str = "claude-sonnet-4-20250514") -> None:
    """
    Interactive REPL for BrainAgent V3.
    Commands: /health  /dream  /teach <concept> :: <truth>  /recall <concept>  /quit
    """
    import sys

    cfg   = AgentConfig(project=project, model=model)
    agent = BrainAgentV3(cfg)
    print(f"\n BrainAgent V3 — project={project!r}\n Type /help for commands.\n")

    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not raw:
            continue

        if raw == "/quit":
            break
        elif raw == "/health":
            print(json.dumps(agent.health(), indent=2, ensure_ascii=False))
        elif raw == "/dream":
            print(json.dumps(agent.run_dream_cycle(), indent=2, ensure_ascii=False))
        elif raw.startswith("/teach "):
            try:
                body  = raw[7:]
                parts = body.split("::")
                node  = agent.teach(parts[0].strip(), parts[1].strip())
                print(f"Taught: {node.concept} → {node.compiled_truth[:80]}")
            except Exception as e:
                print(f"Usage: /teach <concept> :: <truth>   Error: {e}")
        elif raw.startswith("/recall "):
            concept = raw[8:].strip()
            node    = agent.recall(concept)
            if node:
                print(f"[{node.concept}] confidence={node.confidence:.2f}")
                print(f"  Truth  : {node.compiled_truth}")
                print(f"  Timeline ({len(node.timeline)} entries):")
                for t in node.timeline[-3:]:
                    print(f"    {t['ts'][:10]}: {t['evidence'][:80]}")
            else:
                print(f"No semantic node found for '{concept}'.")
        elif raw == "/help":
            print("  /health          — memory + system health report")
            print("  /dream           — run dream cycle consolidation now")
            print("  /teach C :: T    — inject compiled truth for concept C")
            print("  /recall C        — retrieve semantic node for concept C")
            print("  /quit            — exit")
        else:
            resp = agent.run(raw)
            print(f"\nbrain> {resp.answer}")
            print(f"  [{resp.intent.value} | {resp.route.value} | conf={resp.confidence:.2f} | tier={resp.tier}]")
            if resp.entities:
                print(f"  entities : {resp.entities}")
            if resp.temporal_hint:
                print(f"  temporal : {resp.temporal_hint}")
            print()

            # Optional feedback
            fb = input("  feedback (1-5, or Enter to skip)> ").strip()
            if fb:
                try:
                    agent.feedback(resp.episode_id, float(fb))
                    print("  Feedback recorded.")
                except Exception as e:
                    print(f"  Error: {e}")
            print()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — DEMO / QUICK TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.WARNING)

    if "--repl" in sys.argv:
        repl()
        sys.exit(0)

    # ── Quick demo ────────────────────────────────────────────────────────────
    print("=" * 70)
    print("  BrainAgent V3 — Quick Demo")
    print("=" * 70)

    cfg   = AgentConfig(
        project="demo",
        enable_dream_cycle=False,  # off for demo
        enable_council=False,
    )
    agent = BrainAgentV3(cfg)

    # Inject some knowledge
    agent.teach("PicPay", "Fintech brasileiro, foco em PJ e pagamentos Pix.", domain="fintech")
    agent.teach("nuFormer", "Transformer para scoring de crédito; AUC ~0.87 vs LightGBM baseline.", domain="credit")

    queries = [
        "Quem é o PicPay e o que sei sobre eles?",
        "Qual o status do nuFormer?",
        "Análise de fraude nas transações Pix do Inter no Q3 2024",
        "Chargeback rate do Mastercard no último trimestre",
        "O que é machine learning?",
        "Lista todas as empresas no meu brain",
    ]

    for q in queries:
        resp = agent.run(q)
        tier_label = "✓" if resp.tier < 2 else "↗ LLM"
        print(f"\n[{tier_label}] {q[:60]}")
        print(f"  intent : {resp.intent.value}")
        print(f"  route  : {resp.route.value}")
        print(f"  conf   : {resp.confidence:.3f}")
        if resp.entities:
            print(f"  entities : {resp.entities}")
        print(f"  answer[:120]: {resp.answer[:120]}...")

    print("\n" + "─" * 70)
    print("Health report:")
    print(json.dumps(agent.health(), indent=2, ensure_ascii=False))

    # Registry demo
    print("\n" + "─" * 70)
    print("Multi-project registry demo:")
    registry = AgentRegistry()
    registry.register("picpay",   AgentConfig(project="picpay",   enable_dream_cycle=False))
    registry.register("santander",AgentConfig(project="santander",enable_dream_cycle=False))
    print("Projects:", registry.list_projects())

    # Audit trail demo
    print("\n" + "─" * 70)
    audit = AuditTrail(".brainagent/demo/audit.jsonl")
    h = audit.log("agent_run", {"query": "demo", "project": "demo"})
    print(f"Audit hash: {h[:16]}...  chain_valid={audit.verify_chain()}")

    print("\n✓ BrainAgent V3 ready.")
    print("  Run with --repl for interactive mode.")
