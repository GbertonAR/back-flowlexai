## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: tenant.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo de datos B2G principal. Define la entidad Tenant (Jurisdicciones/Parlamentos) 
             en la Base de Datos FlowLex. Incluye la Capa 2 de configuración institucional.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-ONT-003
"""

from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, Dict
from datetime import datetime, timezone

class TenantBase(SQLModel):
    name: str = Field(index=True, max_length=255)
    domain: str = Field(unique=True, index=True, max_length=255)
    schema_name: str = Field(unique=True, index=True, max_length=64, description="Esquema PG aislado para el parlamento")
    plan_type: str = Field(default="starter", description="starter, profesional, soberano")
    is_active: bool = Field(default=True)
    # Capa 2: Configuración Dinámica
    configuration: Dict = Field(
        default_factory=dict, 
        sa_column=Column(JSON), 
        description="Lógica institucional: quórum, tipos de cámara, flujos, etc."
    )

class Tenant(TenantBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
