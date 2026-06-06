## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: compare_router.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Router para el análisis comparativo de versiones legislativas.
FECHA CREACIÓN: 2026-03-25
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-021-DIFF
"""

from fastapi import APIRouter, Depends, Body
from typing import Dict, List
from app.modules.diff.diff_engine import diff_engine
from app.modules.akn.akn_parser import akn_parser
from app.core.logger import forensic_log as logger
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/analyze")
async def analyze_comparison(
    xml_a: str = Body(..., embed=True),
    xml_b: str = Body(..., embed=True),
    current_user = Depends(get_current_user)
):
    """🌐 [REQ] Analiza la diferencia semántica entre dos versiones AKN XML."""
    logger.info(f"🌐 [REQ] Iniciando comparación semántica - Usuario {current_user.id}")
    
    # Extraer artículos de ambos
    articles_a = akn_parser.extract_articles(xml_a)
    articles_b = akn_parser.extract_articles(xml_b)
    
    # Procesar fallbacks si no es XML válido
    if not articles_a:
        articles_a = [{"num": "DocA", "content": xml_a}]
    if not articles_b:
        articles_b = [{"num": "DocB", "content": xml_b}]
    
    comparison = await diff_engine.build_full_diff_report(articles_a, articles_b)
    
    return {
        "summary": "Análisis comparativo completado.",
        "findings": comparison["findings"],
        "executive_summary": comparison["executive_summary"],
        "total_changes": len([c for c in comparison["findings"] if c["status"] != "UNCHANGED"])
    }
