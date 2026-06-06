## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: auditoria.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Endpoints de consulta para logs de auditoría inmutables (WFD Compliance).
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-002
"""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from typing import List, Optional
from app.db.session import get_session
from app.models.auditoria import AuditoriaLog
from app.core.logger import forensic_log as logger
from app.api.deps import get_current_user

router = APIRouter(tags=["Auditoria"])

@router.get("/", response_model=List[AuditoriaLog])
def read_audit_logs(
    tenant_id: Optional[int] = None,
    module: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """🌐 [REQ]: Consultar rastro de auditoría y XAI."""
    statement = select(AuditoriaLog)
    if tenant_id:
        statement = statement.where(AuditoriaLog.tenant_id == tenant_id)
    if module:
        statement = statement.where(AuditoriaLog.module_used == module)
    
    statement = statement.order_by(AuditoriaLog.timestamp.desc()).limit(limit)
    logs = session.exec(statement).all()
    logger.info(f"✅ [OK] Consulta de auditoría: {len(logs)} registros recuperados.")
    return logs
