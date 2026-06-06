## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: bias_report.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo para almacenar reportes de sesgo. (WFD Dir 1.4).
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-004-GAP4
"""

from sqlmodel import SQLModel, Field
from typing import Optional, Dict
from datetime import datetime
import sqlalchemy as sa

class BiasReport(SQLModel, table=True):
    __tablename__ = "bias_report"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True)
    bias_score: float
    metrics_payload: Dict = Field(default_factory=dict, sa_column=sa.Column(sa.JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(description="PASS, WARNING, FAIL")
    recommendations: Optional[str] = None
