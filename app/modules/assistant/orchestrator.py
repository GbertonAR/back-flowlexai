## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: orchestrator.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Orquestador del Agente Legislativo usando LangGraph.
             RAG Gobernado: QueryRewriter → Retrieve → Reranker →
             Analyze → Bias → XAI → Validator → Persist.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-05-12
REF. TICKET: #FS-ONT-006
"""

from typing import Annotated, List, Dict, Optional, TypedDict
from langgraph.graph import StateGraph, END
from app.modules.assistant.vector_store import vector_store
from app.modules.xai.xai_engine import xai_engine
from app.modules.hitl.impact_classifier import impact_classifier
from app.modules.bias.bias_detector import bias_detector
from app.core.logger import forensic_log as logger
from app.db.session import engine
from sqlmodel import Session, select
from app.models.auditoria import AuditoriaLog
from app.models.hitl.hitl_review import HITLReview
from app.models.tenant import Tenant
from app.core.llm import llm_service
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
import json
import hashlib

# ─── Estado del agente ───────────────────────────────────────────────────────

class AgentState(TypedDict):
    request_id: str
    tenant_id: int
    query: str
    rewritten_query: str          # Query reformulada para recuperación legal
    filters: Dict                 # Filtros de metadata ChromaDB (jurisdiccion, tipo_norma)
    context: List[str]
    retrieved_sources: List[Dict]
    retrieval_scores: List[float] # Distancias L2 por chunk (menor = más relevante)
    response: str
    impact_level: str
    requires_hitl: bool
    proposed_response: str
    xai_card: Dict
    bias_report: Dict
    confidence: str               # HIGH | MEDIUM | LOW
    pipeline_trace: Dict          # Trazabilidad completa del pipeline
    status: str


# ─── Nodo 1: Query Rewriter ──────────────────────────────────────────────────

async def query_rewriter_node(state: AgentState):
    logger.info(f"🧠 [WORKFLOW] Nodo: QueryRewriter.")
    llm = llm_service.get_chat_model(temperature=0.0)
    try:
        msg = await llm.ainvoke([
            SystemMessage(content=(
                "Eres un experto en derecho argentino. Reformulá la siguiente consulta "
                "para optimizar la recuperación de normas legales relevantes. "
                "Incluí términos jurídicos precisos como tipo de norma, jurisdicción o artículo si aplica. "
                "Respondé SOLO con la consulta reformulada, sin explicaciones ni comillas."
            )),
            HumanMessage(content=state["query"]),
        ])
        rewritten = msg.content.strip()
        if not rewritten:
            rewritten = state["query"]
    except Exception as e:
        logger.warning(f"⚠️ [WORKFLOW] QueryRewriter falló: {e}. Usando query original.")
        rewritten = state["query"]

    logger.info(f"🧠 [WORKFLOW] Query reescrita: {rewritten[:120]}")
    return {
        "rewritten_query": rewritten,
        "pipeline_trace": {
            "original_query": state["query"],
            "rewritten_query": rewritten,
            "filters": state.get("filters", {}),
        },
    }


# ─── Nodo 2: Retrieve ────────────────────────────────────────────────────────

async def retrieve_node(state: AgentState):
    logger.info(f"🧠 [WORKFLOW] Nodo: Retrieve.")
    query_to_use = state.get("rewritten_query") or state["query"]
    where_filter = state.get("filters") or None

    results = vector_store.query(
        str(state["tenant_id"]),
        query_to_use,
        n_results=10,
        where=where_filter,
    )
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0] or []
    distances = results.get("distances", [[]])[0] or []

    enriched: List[str] = []
    for doc, meta in zip(docs, metas):
        tipo = meta.get("tipo_norma", "")
        jurisdiccion = meta.get("jurisdiccion", "")
        art_num = meta.get("article_num", "")
        section = meta.get("section", "")
        source = meta.get("source", "")

        label_parts: List[str] = []
        if tipo:
            label_parts.append(tipo)
        if jurisdiccion:
            label_parts.append(jurisdiccion)
        if section:
            label_parts.append(section)
        if art_num:
            label_parts.append(f"Art. {art_num}")
        if source:
            label_parts.append(source)

        prefix = f"[{' | '.join(label_parts)}]" if label_parts else ""
        enriched.append(f"{prefix}\n{doc}".strip() if prefix else doc)

    if not enriched:
        enriched = ["Información legislativa genérica."]

    logger.info(f"🧠 [WORKFLOW] Recuperados {len(enriched)} chunks.")
    return {
        "context": enriched,
        "retrieved_sources": metas,
        "retrieval_scores": distances,
    }


# ─── Nodo 3: Reranker ────────────────────────────────────────────────────────

async def reranker_node(state: AgentState):
    """
    Reranker jerárquico-semántico.
    Combina distancia L2 con jerarquía normativa (Art. 31 + Art. 75 inc. 22 CN)
    y penaliza versiones no vigentes de la CN para evitar citar artículos
    renumerados o derogados (ej: Art. 86 texto 1853 != Art. 86 texto 1994).
    """
    logger.info(f"🧠 [WORKFLOW] Nodo: Reranker.")
    from app.modules.assistant.normative_hierarchy import (
        get_hierarchy_level, hierarchy_distance_bonus,
        CN_VIGENTE_VERSION, CN_VERSION_PENALTY,
    )

    context = state["context"]
    sources = state["retrieved_sources"]
    scores = state["retrieval_scores"]

    if not context or context == ["Información legislativa genérica."]:
        return {}

    # Distancia ajustada = L2_raw − bonus_jerárquico + penalidad_CN_histórica
    adjusted: List[tuple] = []
    for c, s, raw_d in zip(context, sources, scores):
        tipo = s.get("tipo_norma", "") if isinstance(s, dict) else ""
        adj_d = raw_d - hierarchy_distance_bonus(get_hierarchy_level(tipo))

        cn_ver = s.get("cn_version", "") if isinstance(s, dict) else ""
        if cn_ver and cn_ver != CN_VIGENTE_VERSION:
            adj_d += CN_VERSION_PENALTY
            logger.warning(
                f"⚠️ [WORKFLOW] CN versión histórica {cn_ver} detectada "
                f"(Arts. renumerados/derogados). Penalidad +{CN_VERSION_PENALTY}."
            )

        adjusted.append((c, s, adj_d, raw_d))

    adjusted.sort(key=lambda x: x[2])

    DISTANCE_THRESHOLD = 1.5
    TOP_K = 5

    filtered = [(c, s, adj, raw) for c, s, adj, raw in adjusted if raw <= DISTANCE_THRESHOLD]
    if not filtered:
        filtered = adjusted

    top = filtered[:TOP_K]

    trace = state.get("pipeline_trace", {})
    trace.update({
        "n_retrieved": len(context),
        "n_after_rerank": len(top),
        "rerank_scores":     [round(t[3], 4) for t in top],
        "rerank_adj_scores": [round(t[2], 4) for t in top],
    })

    logger.info(
        f"\U0001f9e0 [WORKFLOW] Reranker: {len(context)} → {len(top)} chunks "
        f"| adj_scores: {trace['rerank_adj_scores']}"
    )
    return {
        "context": [t[0] for t in top],
        "retrieved_sources": [t[1] for t in top],
        "retrieval_scores": [t[3] for t in top],
        "pipeline_trace": trace,
    }


# ─── Nodo 4: Analyze ─────────────────────────────────────────────────────────

async def analyze_node(state: AgentState):
    logger.info(f"🧠 [WORKFLOW] Nodo: Analyze.")

    rules_str = "Reglas institucionales estándar."
    try:
        with Session(engine) as session:
            tenant = session.get(Tenant, state["tenant_id"])
            if tenant and tenant.configuration:
                rules_str = f"REGLAS DEL PARLAMENTO ({tenant.name}): {json.dumps(tenant.configuration)}"
    except Exception as e:
        logger.warning(f"⚠️ Fallo al cargar configuración: {e}")

    system_prompt = (
        "Eres LexIA, experto jurídico. "
        f"{rules_str}\n\n"
        "REGLAS:\n"
        "1. Detecta idioma automáticamente.\n"
        "2. Citas precisas en español.\n"
        "3. Usa exclusivamente el contexto provisto.\n"
        "4. Tono formal."
    )

    # Context Builder: ordenar fuentes por jerarquía normativa (CN → leyes → decretos)
    # Fundamento: Art. 31 CN + Art. 75 inc. 22 CN (bloque de constitucionalidad)
    from app.modules.assistant.normative_hierarchy import get_hierarchy_level
    sources_meta = state.get("retrieved_sources", [])
    ctx_pairs = list(zip(state["context"], sources_meta or [{}] * len(state["context"])))
    ctx_pairs.sort(
        key=lambda x: get_hierarchy_level(x[1].get("tipo_norma") if isinstance(x[1], dict) else None)
    )
    context_str = "\n\n".join(c for c, _ in ctx_pairs)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"CONTEXTO:\n{context_str}\n\nCONSULTA: {state['query']}"),
    ]

    llm = llm_service.get_chat_model(temperature=0.1)
    ai_msg = await llm.ainvoke(messages)
    response = ai_msg.content

    impact = impact_classifier.classify({"query": state["query"], "response": response})
    requires_hitl = impact_classifier.requires_hitl(impact)

    return {
        "response": response,
        "proposed_response": response,
        "impact_level": impact,
        "requires_hitl": requires_hitl,
    }


# ─── Nodo 5: Bias Check ──────────────────────────────────────────────────────

async def bias_node(state: AgentState):
    report = bias_detector.analyze_response(state["query"], state["response"], state["context"])
    return {"bias_report": report}


# ─── Nodo 6: XAI ─────────────────────────────────────────────────────────────

async def xai_node(state: AgentState):
    sources: List[Dict] = []
    scores = state.get("retrieval_scores", [])

    for i, meta in enumerate(state.get("retrieved_sources", [])[:3]):
        art = meta.get("article_num", "")
        tipo = meta.get("tipo_norma", "")
        jurisdiccion = meta.get("jurisdiccion", "")
        src = meta.get("source", "documento")
        label = f"Art. {art}" if art else ""
        if tipo:
            label = f"{tipo} — {label}" if label else tipo
        if jurisdiccion:
            label = f"{label} ({jurisdiccion})" if label else jurisdiccion
        if not label:
            label = src

        # Convertir distancia L2 a score de relevancia [0,1]
        raw_dist = scores[i] if i < len(scores) else 1.0
        relevance = round(max(0.0, min(1.0, 1.0 - raw_dist / 2.0)), 3)
        sources.append({"name": label, "relevance": relevance})

    if not sources:
        sources = [
            {"name": f"Fragmento {i+1}", "relevance": 0.9}
            for i in range(len(state["context"][:2]))
        ]

    card = xai_engine.generate_explanation(
        state["response"], sources, bias_report=state.get("bias_report")
    )
    return {"xai_card": card.model_dump()}


# ─── Nodo 7: Validator ───────────────────────────────────────────────────────

async def validator_node(state: AgentState):
    """Evalúa si la respuesta está respaldada por las fuentes recuperadas."""
    logger.info(f"🧠 [WORKFLOW] Nodo: Validator.")

    if not state["context"] or state["context"] == ["Información legislativa genérica."]:
        trace = state.get("pipeline_trace", {})
        trace["confidence"] = "LOW"
        return {"confidence": "LOW", "pipeline_trace": trace}

    llm = llm_service.get_chat_model(temperature=0.0)
    try:
        sources_preview = "\n\n".join(state["context"][:3])
        msg = await llm.ainvoke([
            SystemMessage(content=(
                "Evaluá si la RESPUESTA está respaldada por las FUENTES legislativas. "
                "Respondé SOLO con una palabra: HIGH, MEDIUM o LOW."
            )),
            HumanMessage(content=(
                f"FUENTES:\n{sources_preview}\n\n"
                f"RESPUESTA:\n{state['response']}"
            )),
        ])
        confidence = msg.content.strip().upper().split()[0]
        if confidence not in ("HIGH", "MEDIUM", "LOW"):
            confidence = "MEDIUM"
    except Exception as e:
        logger.warning(f"⚠️ [WORKFLOW] Validator falló: {e}")
        confidence = "MEDIUM"

    logger.info(f"🧠 [WORKFLOW] Confianza validada: {confidence}")
    trace = state.get("pipeline_trace", {})
    trace["confidence"] = confidence
    return {"confidence": confidence, "pipeline_trace": trace}


# ─── Nodo 8: Persist ─────────────────────────────────────────────────────────

async def persist_node(state: AgentState):
    try:
        with Session(engine) as session:
            log = AuditoriaLog(
                request_id=state["request_id"],
                tenant_id=state["tenant_id"],
                user_id=1,
                module_used="Assistant",
                action="query",
                content_hash=hashlib.sha256(state["response"].encode()).hexdigest(),
            )
            session.add(log)
            session.commit()
    except Exception as e:
        logger.warning(f"⚠️ [WORKFLOW] Audit log no persistido (no crítico): {e}")
    return {"status": "COMPLETED"}


# ─── Grafo LangGraph ──────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("query_rewrite", query_rewriter_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("rerank", reranker_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("bias_check", bias_node)
workflow.add_node("xai", xai_node)
workflow.add_node("validate", validator_node)
workflow.add_node("persist", persist_node)

workflow.set_entry_point("query_rewrite")
workflow.add_edge("query_rewrite", "retrieve")
workflow.add_edge("retrieve", "rerank")
workflow.add_edge("rerank", "analyze")
workflow.add_edge("analyze", "bias_check")
workflow.add_edge("bias_check", "xai")
workflow.add_edge("xai", "validate")
workflow.add_edge("validate", "persist")
workflow.add_edge("persist", END)

legislative_agent = workflow.compile()


# ─── Entry point público ──────────────────────────────────────────────────────

async def run_assistant(
    tenant_id: int,
    query: str,
    filters: Optional[Dict] = None,
):
    request_id = str(uuid.uuid4())[:8]
    initial_state: AgentState = {
        "request_id": request_id,
        "tenant_id": tenant_id,
        "query": query,
        "rewritten_query": "",
        "filters": filters or {},
        "context": [],
        "retrieved_sources": [],
        "retrieval_scores": [],
        "response": "",
        "impact_level": "LOW",
        "requires_hitl": False,
        "proposed_response": "",
        "xai_card": {},
        "bias_report": {},
        "confidence": "MEDIUM",
        "pipeline_trace": {},
        "status": "STARTING",
    }
    return await legislative_agent.ainvoke(initial_state)
