## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: hitl_review.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo para la cola de revisión humana (Human-in-the-Loop). (WFD Dir 2.1).
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-002-GAP2
"""

from sqlmodel import SQLModel, Field
from typing import Optional, Dict
from datetime import datetime
from enum import Enum
import sqlalchemy as sa

class HITLStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class HITLReview(SQLModel, table=True):
    __tablename__ = "hitl_review"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(index=True)
    impact_level: str = Field(description="LOW, MEDIUM, HIGH, CRITICAL")
    status: HITLStatus = Field(default=HITLStatus.PENDING)
    
    # Payload original que requiere revisión
    original_request: Dict = Field(default_factory=dict, sa_column=sa.Column(sa.JSON))
    ai_proposed_response: str = Field(description="Respuesta que la IA propone y que debe ser validada")
    
    # Datos de la revisión
    reviewer_id: Optional[int] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: int = Field(index=True)
