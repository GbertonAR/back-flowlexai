## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: data_source.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo para el catálogo de fuentes de datos parlamentarias y licencias IP. (WFD Dir 1.5).
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-008-GAP8
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class IPLicenseType(str, Enum):
    OPEN = "OPEN"           # Datos públicos, CC0
    RESTRICTED = "RESTRICTED" # CC-BY, OGL (Requiere atribución)
    COMMERCIAL = "COMMERCIAL" # Requiere contrato (Bloqueado por defecto)
    UNKNOWN = "UNKNOWN"       # Fuente no catalogada (BLOQUEADO)

class DataSource(SQLModel, table=True):
    __tablename__ = "data_source"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    url: Optional[str] = None
    license_type: IPLicenseType = Field(default=IPLicenseType.UNKNOWN)
    owner: str = Field(description="Entidad dueña de los datos (Ej: Cámara de Diputados)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    description: Optional[str] = None
