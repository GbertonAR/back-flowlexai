## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: expediente.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Ontología Legislativa (Capa 1). Define la gestión de Expedientes,
             Proyectos y su ciclo de vida institucional.
FECHA CREACIÓN: 2026-05-06
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-ONT-002
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum

class EstadoExpediente(str, Enum):
    INGRESO = "ingreso"
    COMISION = "comision"
    DICTAMEN = "dictamen"
    SESION = "sesion"
    VOTACION = "votacion"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    ARCHIVADO = "archivado"

class TipoNorma(SQLModel, table=True):
    """Tipos de norma soportados (Ley, Ordenanza, Resolución). Configurable por Tenant."""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100) # e.g., "Ordenanza"
    nivel_jerarquico: int = Field(default=3, description="1: Const, 2: Tratado, 3: Ley, 4: Dec, 5: Res")
    tenant_id: int = Field(foreign_key="tenant.id", index=True)

class Proyecto(SQLModel, table=True):
    """Representa un proyecto legislativo en trámite."""
    id: Optional[int] = Field(default=None, primary_key=True)
    numero_expediente: str = Field(index=True, max_length=50)
    titulo: str = Field(index=True, max_length=500)
    sumario: Optional[str] = Field(default=None)
    texto_completo: Optional[str] = Field(default=None)
    
    fecha_ingreso: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estado: EstadoExpediente = Field(default=EstadoExpediente.INGRESO)
    
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    autor_id: int = Field(foreign_key="legislador.id")
    tipo_norma_id: int = Field(foreign_key="tiponorma.id")
    
    # Metadatos para RAG
    jurisdiccion: Optional[str] = Field(default=None, max_length=100)
    vigente: bool = Field(default=True)

class Dictamen(SQLModel, table=True):
    """Resultado del análisis de un proyecto en una comisión."""
    id: Optional[int] = Field(default=None, primary_key=True)
    proyecto_id: int = Field(foreign_key="proyecto.id")
    comision_id: int = Field(foreign_key="comision.id")
    texto: str
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tipo_dictamen: str = Field(default="mayoria") # mayoria, minoria
