## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: session.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Gestor de sesiones de base de datos SQLModel/SQLAlchemy para PostgreSQL.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-000
"""

import os
from sqlmodel import create_engine, Session
from app.core.config import settings

# En Azure App Service, /home/data/ debe existir antes de que SQLite intente crear el archivo
if os.environ.get("WEBSITE_SITE_NAME") and "sqlite" in settings.DATABASE_URL.lower():
    os.makedirs("/home/data", exist_ok=True)

_is_sqlite = "sqlite" in settings.DATABASE_URL.lower()
_connect_args = {"timeout": 30, "check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

def get_session():
    """Generador de sesiones para dependencias de FastAPI. Registra [REQ] y [OK] o [FAULT] en logs forenses."""
    # 🌐 [REQ]: Setup session
    with Session(engine) as session:
        yield session
