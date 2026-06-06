## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: auditoria.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo de registro inmutable de auditoría para operaciones de Inteligencia artificial (Req. Directrices WFD 2024).
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-002
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, JSON

class AuditoriaLogBase(SQLModel):
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    user_id: int = Field(index=True)
    module_used: str = Field(index=True)
    action: str
    target_resource: Optional[str] = None
    ai_model_version: Optional[str] = None
    # Campo JSON para almacenar metadata y rastro de justificación XAI (explicabilidad de caja negra)
    xai_trace_payload: Optional[dict] = Field(default={}, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

class AuditoriaLog(AuditoriaLogBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(index=True, max_length=8, description="ID de petición FlowState (8 char)")
    content_hash: Optional[str] = Field(default=None, description="Hash SHA-256 para integridad de auditoría")
