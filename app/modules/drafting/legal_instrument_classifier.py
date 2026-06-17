"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: legal_instrument_classifier.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Clasificador de necesidad normativa para el poder legislativo argentino.
             Dado un problema o idea, determina el instrumento jurídico más adecuado:
             A) Nueva ley  B) Modificación de ley existente
             C) Decreto/resolución ejecutiva  D) Cambio de procedimiento administrativo.
             Pipeline LangGraph de 3 nodos: retrieve → classify → xai.
             Citas respaldadas exclusivamente por RAG — cero alucinaciones.
FECHA CREACIÓN: 2026-06-14
ÚLTIMA MODIFICACIÓN: 2026-06-14
REF. TICKET: #FS-CLASSIFIER-001
"""

import uuid
from typing import Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from app.core.llm import llm_service
from app.core.logger import forensic_log as logger
from app.modules.assistant.vector_store import vector_store
from app.modules.xai.xai_engine import xai_engine


# ── Schema de salida estructurada del LLM ──────────────────────────────────────

class _LLMClassification(BaseModel):
    """Contrato de salida para el paso de clasificación. Usado con with_structured_output."""
    nivel1_existe_norma: bool
    nivel1_razon: str
    nivel2_competencia: Literal["Nacional", "Provincial", "Municipal", "Mixta"]
    nivel3_requiere_ley: bool
    recomendacion: Literal["A", "B", "C", "D"]
    recomendacion_titulo: str
    recomendacion_justificacion: str
    normas_citadas: List[str]          # Solo del corpus proporcionado
    norma_a_modificar: Optional[str]   # Obligatorio si recomendacion == "B"
    urgencia: Literal["Alta", "Media", "Baja"]
    riesgo_juridico: Literal["Alto", "Medio", "Bajo"]
    alternativa: Optional[Literal["A", "B", "C", "D"]]
    alternativa_razon: Optional[str]


# ── Response model público (retornado al caller y al endpoint) ─────────────────

class InstrumentClassificationResponse(BaseModel):
    recomendacion: str
    recomendacion_titulo: str
    justificacion: str
    competencia: str
    normas_citadas: List[str]
    norma_a_modificar: Optional[str]
    urgencia: str
    riesgo_juridico: str
    alternativa: Optional[str]
    alternativa_razon: Optional[str]
    nivel1_existe_norma: bool
    nivel1_razon: str
    nivel3_requiere_ley: bool
    fuentes_recuperadas: int
    xai_card: Dict
    disclaimer: str = (
        "AVISO: Análisis asistido por IA basado en el corpus legislativo indexado. "
        "No constituye asesoría jurídica. Debe ser validado por profesionales del derecho "
        "antes de cualquier uso formal."
    )


# ── Estado del grafo ───────────────────────────────────────────────────────────

class ClassificationState(TypedDict):
    request_id: str
    tenant_id: int
    problem_description: str
    area_tematica: str
    retrieved_norms: List[str]
    retrieved_sources: List[Dict]
    retrieval_scores: List[float]
    classification: Dict
    xai_card: Dict
    status: str


# ── Prompt del sistema ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """Sos un experto en técnica legislativa y derecho constitucional argentino con 20 años de experiencia asesorando cuerpos legislativos nacionales y provinciales.

MARCO CONSTITUCIONAL OBLIGATORIO:
• Art. 31 CN — supremacía de la CN y leyes nacionales sobre derecho provincial
• Art. 75 CN — competencias exclusivas del Congreso Nacional (incisos 1–32)
• Arts. 121–128 CN — poderes reservados a las provincias; todo lo no delegado pertenece a ellas
• Art. 99 CN — atribuciones del Poder Ejecutivo (decretos reglamentarios e instructivos)
• Art. 76 CN — prohibición de delegación legislativa (solo excepcionalmente en administración o emergencia pública)

DEFINICIÓN PRECISA DE INSTRUMENTOS:
  A — NUEVA LEY
      Cuando no existe norma que regule el tema Y la materia exige rango legislativo.
      Requiere ley: derechos y obligaciones civiles/penales, creación de organismos, modificación de Códigos (Civil, Penal, Comercial), presupuesto, tributos.

  B — MODIFICACIÓN DE LEY EXISTENTE
      Cuando existe una ley aplicable que necesita actualización, ampliación o corrección.
      SIEMPRE identificar la ley exacta y los artículos a modificar del corpus.

  C — DECRETO O RESOLUCIÓN EJECUTIVA
      Cuando la materia es reglamentaria y no requiere rango de ley.
      No necesita aprobación legislativa. Ejemplos: reglamentar una ley vigente, ajustar procedimientos internos con fundamento legal ya existente.

  D — CAMBIO DE PROCEDIMIENTO ADMINISTRATIVO
      Cuando el problema es de implementación, no normativo.
      La norma existe y es válida pero no se aplica correctamente. Se resuelve con instrucciones, circulares o resoluciones internas, sin instrumento normativo externo.

ÁRBOL DE DECISIÓN — seguirlo en orden estricto:

  NIVEL 1 — ¿Ya existe norma que regule esto en el corpus?
    → SÍ y está vigente y aplicada    → D (problema de implementación)
    → SÍ pero desactualizada/incompleta → B (modificar la existente)
    → NO hay norma                    → continuar a NIVEL 3

  NIVEL 2 — ¿Qué nivel de gobierno tiene competencia?
    → Nacional (Art. 75 CN) | Provincial (Arts. 121–128 CN) | Municipal | Mixta
    → Condiciona la forma del instrumento pero no cambia A/B/C/D

  NIVEL 3 — ¿La materia requiere rango de ley?
    → SÍ → A (o B si existe ley parcial)
    → NO → C

REGLA CRÍTICA — ANTI-ALUCINACIÓN:
  Solo citá normas que aparezcan textualmente en el CORPUS NORMATIVO PROPORCIONADO.
  Si el corpus no contiene normas aplicables: normas_citadas = ["Sin antecedentes en corpus"].
  NUNCA inventar números de ley, artículos, fechas ni organismos.

Respondé en español formal."""


# ── Nodo 1: Recuperación de normas existentes (RAG) ───────────────────────────

async def retrieve_norms_node(state: ClassificationState) -> dict:
    logger.info(f"🧠 [WORKFLOW] [{state['request_id']}] Clasificador: recuperando normas del corpus.")

    query = f"{state['problem_description']} {state['area_tematica']}".strip()
    results = vector_store.query(
        tenant_id=int(state["tenant_id"]),
        query_text=query,
        n_results=8,
    )

    norms = results.get("documents", [[]])[0]
    sources = results.get("metadatas", [[]])[0] or []
    scores = results.get("distances", [[]])[0] or []

    logger.info(f"✅ [OK] [{state['request_id']}] {len(norms)} fragmentos recuperados.")
    return {
        "retrieved_norms": norms,
        "retrieved_sources": sources,
        "retrieval_scores": scores,
    }


# ── Nodo 2: Clasificación con LLM estructurado ────────────────────────────────

async def classify_node(state: ClassificationState) -> dict:
    logger.info(f"🧬 [AGENT] [{state['request_id']}] Determinando instrumento normativo.")

    # Construir corpus con etiquetas de fuente
    sources_meta = state.get("retrieved_sources") or []
    if state["retrieved_norms"]:
        parts = []
        for i, (norm, meta) in enumerate(
            zip(state["retrieved_norms"], sources_meta or [{}] * len(state["retrieved_norms"]))
        ):
            tipo = meta.get("tipo_norma", "") if isinstance(meta, dict) else ""
            fuente = meta.get("source", "") if isinstance(meta, dict) else ""
            label = f"[{tipo} — {fuente}]" if tipo and fuente else f"[Fragmento {i + 1}]"
            parts.append(f"{label}\n{norm[:600]}")
        corpus_str = "\n\n---\n\n".join(parts)
    else:
        corpus_str = "Sin antecedentes en corpus."

    user_prompt = (
        f"PROBLEMA A CLASIFICAR:\n{state['problem_description']}\n\n"
        f"ÁREA TEMÁTICA: {state['area_tematica'] or 'General'}\n\n"
        f"CORPUS NORMATIVO RECUPERADO:\n{corpus_str}"
    )

    llm = llm_service.get_chat_model(temperature=0.0)
    structured_llm = llm.with_structured_output(_LLMClassification)

    try:
        result: _LLMClassification = await structured_llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        classification = result.model_dump()
        logger.info(
            f"✅ [OK] [{state['request_id']}] "
            f"Instrumento: {result.recomendacion} — {result.recomendacion_titulo} | "
            f"Competencia: {result.nivel2_competencia} | "
            f"Norma existente: {result.nivel1_existe_norma}"
        )
    except Exception as e:
        logger.error(f"❌ [FAULT] [{state['request_id']}] Error LLM en clasificación: {e}")
        classification = {
            "nivel1_existe_norma": False,
            "nivel1_razon": f"Error en clasificación automática: {e}",
            "nivel2_competencia": "Nacional",
            "nivel3_requiere_ley": True,
            "recomendacion": "A",
            "recomendacion_titulo": "Revisión manual requerida",
            "recomendacion_justificacion": "El clasificador encontró un error. Se requiere revisión jurídica manual.",
            "normas_citadas": [],
            "norma_a_modificar": None,
            "urgencia": "Media",
            "riesgo_juridico": "Alto",
            "alternativa": None,
            "alternativa_razon": None,
        }

    return {"classification": classification, "status": "CLASSIFIED"}


# ── Nodo 3: Tarjeta XAI ───────────────────────────────────────────────────────

async def xai_node(state: ClassificationState) -> dict:
    logger.info(f"🧠 [WORKFLOW] [{state['request_id']}] Generando tarjeta XAI.")

    scores = state.get("retrieval_scores", [])
    sources_for_xai = []
    for i, meta in enumerate((state.get("retrieved_sources") or [])[:3]):
        if not isinstance(meta, dict):
            continue
        tipo = meta.get("tipo_norma", "")
        fuente = meta.get("source", f"Fuente {i + 1}")
        label = f"{tipo} — {fuente}" if tipo else fuente
        raw_dist = scores[i] if i < len(scores) else 0.5
        # Convertir distancia coseno a relevancia [0,1]
        relevance = round(max(0.0, min(1.0, 1.0 - raw_dist)), 3)
        sources_for_xai.append({"name": label, "relevance": relevance})

    if not sources_for_xai:
        sources_for_xai = [{"name": "Sin corpus legislativo relevante", "relevance": 0.0}]

    clf = state.get("classification", {})
    summary = (
        f"Instrumento recomendado: {clf.get('recomendacion', '?')} — "
        f"{clf.get('recomendacion_titulo', '')}. "
        f"Competencia: {clf.get('nivel2_competencia', '')}. "
        f"{clf.get('recomendacion_justificacion', '')[:300]}"
    )

    card = xai_engine.generate_explanation(
        response_text=summary,
        sources_used=sources_for_xai,
    )
    return {"xai_card": card.model_dump()}


# ── Compilación del grafo ──────────────────────────────────────────────────────

_builder = StateGraph(ClassificationState)
_builder.add_node("retrieve_norms", retrieve_norms_node)
_builder.add_node("classify", classify_node)
_builder.add_node("xai", xai_node)

_builder.set_entry_point("retrieve_norms")
_builder.add_edge("retrieve_norms", "classify")
_builder.add_edge("classify", "xai")
_builder.add_edge("xai", END)

instrument_classifier = _builder.compile()


# ── Entry point público ────────────────────────────────────────────────────────

async def run_instrument_classification(
    tenant_id: int,
    problem_description: str,
    area_tematica: str = "",
) -> InstrumentClassificationResponse:
    request_id = str(uuid.uuid4())[:8]
    logger.info(
        f"🌐 [REQ] [{request_id}] Clasificación de instrumento normativo | "
        f"Tenant: {tenant_id} | Área: {area_tematica or 'General'}"
    )

    initial_state: ClassificationState = {
        "request_id": request_id,
        "tenant_id": tenant_id,
        "problem_description": problem_description,
        "area_tematica": area_tematica,
        "retrieved_norms": [],
        "retrieved_sources": [],
        "retrieval_scores": [],
        "classification": {},
        "xai_card": {},
        "status": "STARTING",
    }

    final_state = await instrument_classifier.ainvoke(initial_state)
    clf = final_state["classification"]

    return InstrumentClassificationResponse(
        recomendacion=clf.get("recomendacion", "A"),
        recomendacion_titulo=clf.get("recomendacion_titulo", ""),
        justificacion=clf.get("recomendacion_justificacion", ""),
        competencia=clf.get("nivel2_competencia", "Nacional"),
        normas_citadas=clf.get("normas_citadas", []),
        norma_a_modificar=clf.get("norma_a_modificar"),
        urgencia=clf.get("urgencia", "Media"),
        riesgo_juridico=clf.get("riesgo_juridico", "Medio"),
        alternativa=clf.get("alternativa"),
        alternativa_razon=clf.get("alternativa_razon"),
        nivel1_existe_norma=clf.get("nivel1_existe_norma", False),
        nivel1_razon=clf.get("nivel1_razon", ""),
        nivel3_requiere_ley=clf.get("nivel3_requiere_ley", True),
        fuentes_recuperadas=len(final_state["retrieved_norms"]),
        xai_card=final_state["xai_card"],
    )
