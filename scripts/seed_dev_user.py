## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: seed_dev_user.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script para inicializar un usuario administrador en el entorno de desarrollo.
FECHA CREACIÓN: 2026-03-25
"""

import sys
import os
# Añadir el path del backend para importar módulos de la app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, select
from app.db.session import engine
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.core.security import hash_password
from app.core.logger import forensic_log as logger

def seed():
    with Session(engine) as session:
        # 1. Crear Tenant de Desarrollo si no existe
        tenant = session.exec(select(Tenant).where(Tenant.id == 1)).first()
        if not tenant:
            logger.info("🧬 [AGENT] Creando Tenant de Desarrollo (ID: 1)...")
            tenant = Tenant(
                id=1,
                name="FlowState Dev Org",
                domain="dev.flowlex.ai",
                schema_name="public",
                is_active=True
            )
            session.add(tenant)
            session.commit()
            session.refresh(tenant)

        # 2. Crear Usuario Admin si no existe
        user = session.exec(select(User).where(User.email == "admin@flowlex.ai")).first()
        if not user:
            logger.info("🧬 [AGENT] Creando Usuario Admin (admin@flowlex.ai)...")
            user = User(
                email="admin@flowlex.ai",
                full_name="Administrador LexIA",
                hashed_password=hash_password("admin"),
                role=UserRole.admin,
                tenant_id=1,
                is_active=True
            )
            session.add(user)
            session.commit()
            logger.info("✅ [OK] Usuario Admin creado exitosamente. Clave: admin")
        else:
            logger.info("✅ [OK] El usuario admin@flowlex.ai ya existe.")

if __name__ == "__main__":
    seed()
