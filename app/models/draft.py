## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: draft.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo de persistencia para borradores legislativos.
             Gestiona el ciclo de vida del documento antes de su radicación formal.
FECHA CREACIÓN: 2026-05-13
ÚLTIMA MODIFICACIÓN: 2026-05-13
REF. TICKET: #FS-DRAFT-MODEL
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class Draft(SQLModel, table=True):
    """Representa un borrador de proyecto legislativo en proceso de redacción."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    user_id: int = Field(foreign_key="lexia_user.id", index=True)
    
    titulo: str = Field(index=True, max_length=255)
    contenido: str = Field(default="")
    
    # Métricas de Auditoría Ética
    status: str = Field(default="DRAFT") # DRAFT, IN_REVIEW, APPROVED
    bias_score: float = Field(default=0.0)
    
    # Metadata Temporal
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        schema_extra = {
            "example": {
                "titulo": "Proyecto de Ley de Fomento a la IA",
                "status": "DRAFT",
                "bias_score": 0.15
            }
        }
