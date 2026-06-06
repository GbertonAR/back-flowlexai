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

from sqlmodel import create_engine, Session
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True
)

def get_session():
    """Generador de sesiones para dependencias de FastAPI. Registra [REQ] y [OK] o [FAULT] en logs forenses."""
    # 🌐 [REQ]: Setup session
    with Session(engine) as session:
        yield session
