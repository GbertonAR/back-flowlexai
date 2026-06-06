## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: diff_engine.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Motor de comparación semántica legislativa (Fase 3.3).
             Identifica cambios estructurales y genera explicaciones de impacto con LLM.
FECHA CREACIÓN: 2026-03-25
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-021-DIFF
"""

import json
from typing import List, Dict
from app.core.llm import llm_service
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.logger import forensic_log as logger

_DIFF_SYSTEM_PROMPT = """Eres un experto en derecho comparado y análisis normativo.
Tu tarea es analizar dos versiones de un mismo artículo legal e identificar los cambios jurídicos sustanciales.

Responde EXCLUSIVAMENTE con un JSON válido con esta estructura:
{
  "change_type": "MODIFIED" | "UNCHANGED",
  "impact_summary": "Breve explicación del cambio jurídico (ej: endurecimiento de penas)",
  "technical_diff": "Resumen técnico de las palabras modificadas",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "tags": ["lista de etiquetas relacionadas al cambio"]
}"""

class SemanticDiffEngine:
    """
    Motor de análisis comparativo entre versiones de documentos legislativos.
    """

    async def compare_article_versions(self, text_a: str, text_b: str) -> Dict:
        """Usa LLM para analizar la diferencia semántica entre dos textos."""
        if text_a.strip() == text_b.strip():
            return {
                "change_type": "UNCHANGED",
                "impact_summary": "Sin cambios detectados.",
                "technical_diff": "",
                "risk_level": "LOW",
                "tags": []
            }

        prompt = (
            f"VERSIÓN ANTERIOR:\n{text_a}\n\n"
            f"VERSIÓN NUEVA:\n{text_b}\n\n"
            "Analiza el impacto jurídico del cambio."
        )

        try:
            messages = [
                SystemMessage(content=_DIFF_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            llm = llm_service.get_chat_model(temperature=0.0)
            result = await llm.ainvoke(messages)
            content = result.content.strip()
            
            # Limpiar bloques markdown si existen
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                    
            return json.loads(content)
        except Exception as e:
            logger.error(f"❌ [FAULT] Error en SemanticDiffEngine: {e}")
            return {
                "change_type": "ERROR",
                "impact_summary": f"Fallo en el análisis: {str(e)}",
                "technical_diff": "N/A",
                "risk_level": "UNKNOWN",
                "tags": ["error"]
            }

    async def build_full_diff_report(self, articles_a: List[Dict], articles_b: List[Dict]) -> Dict:
        """Compara dos conjuntos de artículos (AKN) y genera un reporte consolidado con Delta de Impacto."""
        import asyncio
        report = []
        map_a = {a.get("num") or a.get("id"): a for a in articles_a}
        map_b = {b.get("num") or b.get("id"): b for b in articles_b}

        tasks = []
        item_keys = []

        # Preparar tareas para artículos en B (nuevos o modificados)
        for key, art_b in map_b.items():
            if key in map_a:
                art_a = map_a[key]
                tasks.append(self.compare_article_versions(art_a["content"], art_b["content"]))
                item_keys.append((key, art_b.get("heading", ""), "MODIFIED"))
            else:
                report.append({
                    "item": key,
                    "heading": art_b.get("heading", ""),
                    "status": "ADDED",
                    "analysis": {
                        "change_type": "ADDED",
                        "impact_summary": "Artículo incorporado en la nueva versión.",
                        "risk_level": "MEDIUM",
                        "tags": ["new_content"]
                    }
                })

        # Ejecutar comparaciones en paralelo
        if tasks:
            logger.info(f"🧠 [WORKFLOW] Iniciando {len(tasks)} comparaciones semánticas en paralelo.")
            results = await asyncio.gather(*tasks)
            for (key, heading, _), diff in zip(item_keys, results):
                report.append({
                    "item": key,
                    "heading": heading,
                    "status": diff["change_type"],
                    "analysis": diff
                })

        # Identificar eliminados
        for key in map_a:
            if key not in map_b:
                report.append({
                    "item": key,
                    "heading": map_a[key].get("heading", ""),
                    "status": "DELETED",
                    "analysis": {
                        "change_type": "DELETED",
                        "impact_summary": "Artículo derogado o eliminado.",
                        "risk_level": "HIGH",
                        "tags": ["derogated"]
                    }
                })

        # Generar Delta de Impacto Global
        summary = await self.generate_impact_delta(report)
        
        return {
            "findings": report,
            "executive_summary": summary
        }

    async def generate_impact_delta(self, report: List[Dict]) -> str:
        """Genera un resumen ejecutivo global de toda la comparación legislativa."""
        changed_items = [r for r in report if r["status"] != "UNCHANGED"]
        if not changed_items:
            return "No se detectaron cambios sustanciales entre las versiones analizadas."

        logger.info(f"🧠 [WORKFLOW] Generando Impact Delta para {len(changed_items)} cambios.")
        
        changes_summary = "\n".join([
            f"- {c['item']} ({c['status']}): {c['analysis'].get('impact_summary', '')}" 
            for c in changed_items[:10] # Limitar a los primeros 10 para el prompt
        ])

        system_prompt = (
            "Eres el Analista Principal de Riesgo Normativo de FlowLex AI. "
            "Tu tarea es consolidar una serie de cambios legislativos en un resumen ejecutivo de ALTO NIVEL "
            "para un Ministro o Legislador. Enfócate en el 'alma' de la reforma y sus implicancias sociales/jurídicas."
        )
        
        prompt = f"RESUMEN DE CAMBIOS DETECTADOS:\n{changes_summary}\n\nPor favor, genera una conclusión de impacto global de máximo 3 párrafos."
        
        try:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
            llm = llm_service.get_chat_model(temperature=0.3)
            result = await llm.ainvoke(messages)
            return result.content
        except Exception as e:
            logger.error(f"❌ [FAULT] Error generando Impact Delta: {e}")
            return "Error al generar el resumen ejecutivo global."

diff_engine = SemanticDiffEngine()
