## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: drafting_orchestrator.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Orquestador especializado en redacción asistida de normativa.
             Implementa el flujo de generación estructurada (Visto/Considerando).
FECHA CREACIÓN: 2026-05-06
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-AI-DRAFT
"""

from typing import List, Dict, TypedDict
from langgraph.graph import StateGraph, END
from app.core.llm import llm_service
from app.modules.assistant.vector_store import vector_store
from app.core.logger import forensic_log as logger
from langchain_core.messages import SystemMessage, HumanMessage

class DraftingState(TypedDict):
    tenant_id: int
    user_id: int
    topic: str
    context: List[str]
    draft: str
    rules: Dict
    status: str

async def retrieve_context(state: DraftingState):
    logger.info(f"🧠 [WORKFLOW] Recuperando antecedentes legislativos para Tenant {state['tenant_id']}: '{state['topic']}'")
    results = vector_store.query(str(state["tenant_id"]), state["topic"], n_results=5)
    context_count = len(results.get("documents", [[]])[0])
    logger.info(f"✅ [OK] {context_count} fragmentos de contexto recuperados para la redacción.")
    return {"context": results.get("documents", [[]])[0]}

async def draft_node(state: DraftingState):
    logger.info(f"🧬 [AGENT] Iniciando proceso creativo de Redacción Asistida.")
    
    rules_str = f"Reglas Institucionales: {state['rules']}" if state['rules'] else "Reglas estándar de técnica legislativa."
    
    system_prompt = (
        "Eres un experto Senior en técnica legislativa argentina de FlowLexAI.\n"
        "Tu tarea es redactar proyectos de ley/ordenanza con alta precisión jurídica.\n\n"
        "ESTRUCTURA OBLIGATORIA (Formato Markdown):\n"
        "1. VISTO: Referencia a leyes/normas existentes.\n"
        "2. CONSIDERANDO: Fundamentos políticos, sociales y técnicos.\n"
        "3. PROYECTO DE [TIPO]: El articulado final.\n\n"
        f"CONTEXTO SOBERANO:\n{state['context']}\n\n"
        f"REGLAS DEL TENANT:\n{rules_str}\n\n"
        "IMPORTANTE: Mantén un lenguaje formal, técnico y soberano."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Redactar proyecto sobre: {state['topic']}")
    ]
    
    llm = llm_service.get_chat_model(temperature=0.3)
    logger.info(f"🧠 [WORKFLOW] Invocando LLM para síntesis normativa...")
    response = await llm.ainvoke(messages)
    
    logger.info(f"✅ [OK] Borrador generado exitosamente ({len(response.content)} caracteres).")
    return {"draft": response.content}

# Grafo de Redacción
builder = StateGraph(DraftingState)
builder.add_node("retrieve", retrieve_context)
builder.add_node("draft", draft_node)
builder.set_entry_point("retrieve")
builder.add_edge("retrieve", "draft")
builder.add_edge("draft", END)

drafting_agent = builder.compile()

async def run_drafting(tenant_id: int, user_id: int, topic: str, rules: Dict = None):
    logger.info(f"🌐 [REQ] Nueva solicitud de Redacción Asistida (Usuario: {user_id})")
    initial_state = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "topic": topic,
        "context": [],
        "draft": "",
        "rules": rules or {},
        "status": "DRAFTING"
    }
    return await drafting_agent.ainvoke(initial_state)
