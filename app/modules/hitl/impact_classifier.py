## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: impact_classifier.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Clasificador lógico de impacto para disparar revisiones HITL. (WFD Dir 2.1).
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-002-GAP2
"""

from typing import Dict
from app.core.logger import forensic_log as logger

class ImpactClassifier:
    """
    Analiza la intención y el contenido del request para determinar el nivel de riesgo/impacto.
    """
    
    CRITICAL_KEYWORDS = ["aprobación", "sanción", "constitucionalidad", "seguridad nacional", "voto"]
    HIGH_KEYWORDS = ["reforma", "presupuesto", "derechos humanos", "penal"]

    @staticmethod
    def classify(request_payload: Dict) -> str:
        """
        🧬 [AGENT] Clasificación semántica de impacto legal usando LLM.
        """
        from app.core.llm import llm_service
        from langchain_core.messages import SystemMessage, HumanMessage
        
        query = request_payload.get("query", "")
        response = request_payload.get("response", "")
        
        system_prompt = (
            "Eres el Auditor de Riesgo Legislativo de FlowLex AI (Sovereign Authority Mode). "
            "Tu misión es clasificar el impacto legal y social de una consulta/respuesta basándote en directrices de la WFD.\n\n"
            "CATEGORÍAS DE IMPACTO:\n"
            "- CRITICAL: Cuestiones de constitucionalidad, derogación de leyes fundamentales, seguridad nacional, vida/muerte, o impacto en millones de ciudadanos.\n"
            "- HIGH: Reformas de códigos (Penal, Civil, Comercial), presupuestos nacionales, derechos laborales o humanos directos.\n"
            "- MEDIUM: Regulaciones administrativas, normativas locales, cambios menores en procedimientos legislativos.\n"
            "- LOW: Consultas conceptuales, aclaraciones de términos ya vigentes, dudas de dominio público sin cambio de estado.\n\n"
            "INSTRUCCIÓN: Responde EXCLUSIVAMENTE con la palabra de la categoría."
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"CONSULTA: {query}\nRESPUESTA: {response}")
        ]
        
        try:
            llm = llm_service.get_chat_model(temperature=0.0)
            ai_msg = llm.invoke(messages)
            impact = ai_msg.content.strip().upper()
            
            # Validación de salida segura
            if impact not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                logger.warning(f"⚠️ [WARNING] LLM retornó categoría inválida: {impact}. Fallback a LOW.")
                return "LOW"
            
            logger.info(f"✅ [OK] Impacto clasificado semánticamente: {impact}")
            return impact
        except Exception as e:
            logger.error(f"❌ [FAULT] Error en clasificación LLM: {str(e)}. Fallback a heurística.")
            # Fallback a heurística simple si el LLM falla
            text = f"{query} {response}".lower()
            if any(word in text for word in ImpactClassifier.CRITICAL_KEYWORDS):
                return "CRITICAL"
            return "LOW"

    @staticmethod
    def requires_hitl(impact_level: str) -> bool:
        return impact_level in ["HIGH", "CRITICAL"]

impact_classifier = ImpactClassifier()
