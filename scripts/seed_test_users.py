## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: seed_test_users.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script para inicializar usuarios de prueba con diferentes roles (RBAC).
FECHA CREACIÓN: 2026-04-29
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, select
from app.db.session import engine
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.expediente import TipoNorma
from app.core.security import hash_password
from app.core.logger import forensic_log as logger

def seed():
    with Session(engine) as session:
        # Asegurar Tenant
        tenant = session.exec(select(Tenant).where(Tenant.id == 1)).first()
        if not tenant:
            tenant = Tenant(id=1, name="FlowState Dev Org", domain="dev.flowlex.ai", schema_name="public", is_active=True)
            session.add(tenant)
            session.commit()
            session.refresh(tenant)

        test_users = [
            {"email": "admin@flowlex.ai", "name": "Admin LexIA", "role": UserRole.admin, "pwd": "admin"},
            {"email": "legislator@flowlex.ai", "name": "Diputado Nacional", "role": UserRole.legislator, "pwd": "legislator123"},
            {"email": "analyst@flowlex.ai", "name": "Analista Jurídico", "role": UserRole.analyst, "pwd": "analyst123"},
            {"email": "readonly@flowlex.ai", "name": "Auditor Invitado", "role": UserRole.readonly, "pwd": "readonly123"},
        ]

        for u_data in test_users:
            user = session.exec(select(User).where(User.email == u_data["email"])).first()
            if not user:
                logger.info(f"🧬 [AGENT] Creando usuario {u_data['email']}...")
                user = User(
                    email=u_data["email"],
                    full_name=u_data["name"],
                    hashed_password=hash_password(u_data["pwd"]),
                    role=u_data["role"],
                    tenant_id=1,
                    is_active=True
                )
                session.add(user)
        
        session.commit()
        logger.info("✅ [OK] Usuarios de prueba inicializados correctamente.")

        tipos = [
            {"id": 1, "nombre": "Constitución", "nivel_jerarquico": 1},
            {"id": 2, "nombre": "Ley",          "nivel_jerarquico": 3},
            {"id": 3, "nombre": "Decreto",      "nivel_jerarquico": 4},
            {"id": 4, "nombre": "Reglamento",   "nivel_jerarquico": 4},
            {"id": 5, "nombre": "Resolución",   "nivel_jerarquico": 5},
            {"id": 6, "nombre": "Ordenanza",    "nivel_jerarquico": 4},
        ]
        for t in tipos:
            if not session.get(TipoNorma, t["id"]):
                session.add(TipoNorma(id=t["id"], nombre=t["nombre"], nivel_jerarquico=t["nivel_jerarquico"], tenant_id=1))
        session.commit()
        logger.info("✅ [OK] TipoNorma inicializados (6 tipos).")

if __name__ == "__main__":
    seed()
