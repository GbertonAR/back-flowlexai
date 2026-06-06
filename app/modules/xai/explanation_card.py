## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: explanation_card.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo de datos para la Tarjeta de Explicabilidad XAI. (WFD Dir 5.2).
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-001-GAP1
"""

from pydantic import BaseModel
from typing import List, Dict, Optional

class XAISourceWeight(BaseModel):
    source_name: str
    weight: float  # 0.0 to 1.0
    impact_level: str # LOW, MEDIUM, HIGH

class ExplanationCard(BaseModel):
    confidence_score: float  # 0.0 to 1.0
    reasoning_steps: List[str]
    sources: List[XAISourceWeight]
    limitations: List[str]
    wfd_compliance_ref: str = "Dir. 5.2 — Explicabilidad Algorítmica"
    ai_model_version: str
    generation_timestamp: str
    bias_summary: Optional[Dict] = None  # Agregado en Fase 1
