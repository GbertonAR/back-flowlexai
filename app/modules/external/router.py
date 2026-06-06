## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: router.py (External)
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Router para la gestión de conectores externos (HORUS, SIL).
FECHA CREACIÓN: 2026-03-25
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-023-INT
"""

from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any
from app.api.deps import get_current_user
from app.core.logger import forensic_log as logger
from .horus_connector import horus_connector
from .sil_connector import sil_connector

router = APIRouter(prefix="/external")

@router.post("/horus/sync")
async def sync_horus(
    payload: Dict[str, Any] = Body(...),
    current_user = Depends(get_current_user)
):
    """🌐 [REQ] Sincronizar documento desde el sistema HORUS."""
    logger.info(f"🌐 [REQ] Iniciando sync HORUS - Usuario {current_user.id}")
    result = await horus_connector.sync_document(payload)
    return result

@router.post("/sil/import")
async def import_sil(
    document_id: str = Body(..., embed=True),
    current_user = Depends(get_current_user)
):
    """🌐 [REQ] Importar expediente desde el sistema SIL."""
    logger.info(f"🌐 [REQ] Iniciando import SIL - Usuario {current_user.id} - DocID: {document_id}")
    result = await sil_connector.fetch_and_import(document_id)
    return result
