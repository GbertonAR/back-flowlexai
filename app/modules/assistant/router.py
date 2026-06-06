## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: router.py (Assistant)
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Endpoints para la interacción con el Asistente Legislativo AI.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-006-AI
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.modules.assistant.orchestrator import run_assistant
from app.api.deps import get_current_user
from app.models.user import User
from app.core.logger import forensic_log as logger

router = APIRouter(prefix="/assistant", tags=["Assistant"])

class AssistantRequest(BaseModel):
    tenant_id: int
    query: str
    jurisdiccion: Optional[str] = None   # Filtro: "Nacional", "CABA", "Buenos Aires", etc.
    tipo_norma: Optional[str] = None     # Filtro: "Ley", "Decreto", "Reglamento", etc.

class SearchRequest(BaseModel):
    tenant_id: int
    query: str
    limit: int = 5

@router.post("/analyze")
async def analyze_legislative_query(
    req: AssistantRequest,
    current_user: User = Depends(get_current_user)
):
    logger.info(f"🌐 [REQ] Analizando consulta legislativa para Tenant: {req.tenant_id}")

    # Construir filtros ChromaDB si se especificaron
    filters: Optional[dict] = None
    if req.jurisdiccion and req.tipo_norma:
        filters = {"$and": [
            {"jurisdiccion": {"$eq": req.jurisdiccion}},
            {"tipo_norma": {"$eq": req.tipo_norma}},
        ]}
    elif req.jurisdiccion:
        filters = {"jurisdiccion": {"$eq": req.jurisdiccion}}
    elif req.tipo_norma:
        filters = {"tipo_norma": {"$eq": req.tipo_norma}}

    try:
        result = await run_assistant(req.tenant_id, req.query, filters=filters)

        # Construir lista de fuentes con score de relevancia
        fuentes = []
        sources = result.get("retrieved_sources", [])
        scores = result.get("retrieval_scores", [])
        for i, src in enumerate(sources):
            raw_dist = scores[i] if i < len(scores) else 1.0
            relevance = round(max(0.0, min(1.0, 1.0 - raw_dist / 2.0)), 3)
            fuentes.append({
                "documento": src.get("source", ""),
                "articulo": f"Art. {src.get('article_num', '')}" if src.get("article_num") else "",
                "jurisdiccion": src.get("jurisdiccion", ""),
                "tipo_norma": src.get("tipo_norma", ""),
                "score": relevance,
            })

        return {
            "request_id": result["request_id"],
            "response": result["response"],
            "impact_level": result["impact_level"],
            "requires_hitl": result["requires_hitl"],
            "confidence": result.get("confidence", "MEDIUM"),
            "xai_card": result["xai_card"],
            "fuentes": fuentes,
            "pipeline_trace": result.get("pipeline_trace", {}),
        }
    except Exception as e:
        logger.error(f"❌ [FAULT] Error en el orquestador legislativo: {e}")
        raise HTTPException(status_code=500, detail="Internal AI Error")

@router.post("/search")
async def semantic_search(
    req: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """🌐 [REQ] Búsqueda semántica directa en la base de conocimiento."""
    from app.modules.assistant.vector_store import vector_store
    logger.info(f"🧠 [WORKFLOW] Búsqueda semántica para Tenant: {req.tenant_id} | Query: {req.query}")
    try:
        results = vector_store.query(str(req.tenant_id), req.query, n_results=req.limit)
        # Adaptar respuesta para el frontend
        formatted_results = []
        if results and "documents" in results:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0
                })
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"❌ [FAULT] Error en búsqueda semántica: {e}")
        raise HTTPException(status_code=500, detail="Search Error")
