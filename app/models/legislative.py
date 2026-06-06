## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: legislative.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Ontología Legislativa (Capa 1). Define las entidades de poder político:
             Bloques, Comisiones y la vinculación de Legisladores.
FECHA CREACIÓN: 2026-05-06
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-ONT-001
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, timezone

class Bloque(SQLModel, table=True):
    """Representa un bloque político dentro de un Parlamento (Tenant)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, max_length=255)
    sigla: Optional[str] = Field(default=None, max_length=20)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    color_hex: Optional[str] = Field(default="#000000", max_length=7)
    
    # Relaciones
    # legisladores: List["Legislador"] = Relationship(back_populates="bloque")

class Comision(SQLModel, table=True):
    """Comisiones legislativas donde se analizan los proyectos."""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, max_length=255)
    descripcion: Optional[str] = Field(default=None)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    es_permanente: bool = Field(default=True)

class Legislador(SQLModel, table=True):
    """Entidad que vincula a un Usuario con un rol político y un Bloque."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="lexia_user.id", unique=True)
    bloque_id: Optional[int] = Field(default=None, foreign_key="bloque.id")
    distrito: Optional[str] = Field(default=None, max_length=100)
    biografia: Optional[str] = Field(default=None)
    
    # Relaciones
    # bloque: Optional[Bloque] = Relationship(back_populates="legisladores")
