## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: data_lineage.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo para la trazabilidad de datos (Lineage) en inferencias de IA. (WFD Dir 1.5).
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-008-GAP8
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid

class DataLineage(SQLModel, table=True):
    __tablename__ = "data_lineage"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: str = Field(index=True, description="Enlace al log forense de la petición")
    data_source_id: int = Field(foreign_key="data_source.id")
    document_ref: str = Field(description="Identificador del documento específico consumido")
    usage_context: str = Field(description="Contexto del uso (Ej: Semantic Search, Summarization)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: int = Field(index=True)
