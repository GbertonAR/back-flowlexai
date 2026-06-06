## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: subscription.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo de datos para suscripciones a alertas regulatorias. Fase 3.2.
FECHA CREACIÓN: 2026-03-25
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-020-ALERTS
"""

from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON, Column
from datetime import datetime

class Subscription(SQLModel, table=True):
    __tablename__ = "lexia_subscription"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True)
    user_id: int = Field(index=True)
    
    # Lista de palabras clave o áreas de interés
    keywords: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    
    # Configuración de notificación
    is_active: bool = Field(default=True)
    notify_email: bool = Field(default=True)
    notify_webhook: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
