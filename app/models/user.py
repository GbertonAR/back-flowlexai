## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: user.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo de datos del Usuario con RBAC. Roles: admin, legislator,
             analyst, readonly. Vinculado a Tenant para aislamiento multi-org.
FECHA CREACIÓN: 2026-03-15
ÚLTIMA MODIFICACIÓN: 2026-03-15
REF. TICKET: #FS-012-IAM
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


class UserRole(str, Enum):
    admin      = "admin"
    legislator = "legislator"
    analyst    = "analyst"
    readonly   = "readonly"


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, max_length=320)
    full_name: str = Field(default="", max_length=255)
    role: UserRole = Field(default=UserRole.readonly)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    __tablename__ = "lexia_user"
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Schemas Pydantic para la API ───────────────────────────────────────────────
class UserRegister(SQLModel):
    email: str
    password: str
    full_name: str = ""
    role: UserRole = UserRole.readonly
    tenant_id: Optional[int] = None


class UserPublic(SQLModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    tenant_id: Optional[int]
    is_active: bool


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos
