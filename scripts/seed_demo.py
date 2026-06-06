"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: seed_demo.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script de seed idempotente. Crea el usuario demo y
             envía notificación por email al administrador.
             Se ejecuta desde el directorio backend/:
               python scripts/seed_demo.py
FECHA CREACIÓN: 2026-05-12
ÚLTIMA MODIFICACIÓN: 2026-05-12
REF. TICKET: #FS-GCP-001
"""

import sys
import os

# Agrega el directorio backend/ al path para que los imports de app.* funcionen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, SQLModel

from app.db.session import engine
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.core.security import hash_password
from app.core.email_service import send_demo_user_notification
from app.core.logger import forensic_log as logger

# ── Credenciales del usuario demo ─────────────────────
DEMO_EMAIL    = "demo@flowlexai.com"
DEMO_PASSWORD = "demo123!"
DEMO_NAME     = "Usuario Demo"
DEMO_ROLE     = UserRole.readonly
DEMO_TENANT   = 1


def _ensure_tenant(session: Session) -> None:
    tenant = session.get(Tenant, DEMO_TENANT)
    if not tenant:
        logger.info("🧠 [WORKFLOW] Creando Tenant #1 (Demo) para el seed.")
        tenant = Tenant(
            id=DEMO_TENANT,
            name="Parlamento Principal",
            domain="flowlexai.com",
            schema_name="public",
            plan_type="starter",
        )
        session.add(tenant)
        session.commit()


def seed() -> None:
    # Crea tablas si no existen (entorno fresco)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.email == DEMO_EMAIL)
        ).first()

        if existing:
            logger.info(f"✅ [OK] Usuario demo ya existe ({DEMO_EMAIL}), seed omitido.")
            return

        _ensure_tenant(session)

        demo_user = User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name=DEMO_NAME,
            role=DEMO_ROLE,
            tenant_id=DEMO_TENANT,
        )
        session.add(demo_user)
        session.commit()
        session.refresh(demo_user)

        logger.info(f"✅ [OK] Usuario demo creado | email={DEMO_EMAIL} | id={demo_user.id}")

    # Envía notificación por email (fuera del bloque de sesión)
    send_demo_user_notification(DEMO_EMAIL, DEMO_NAME)


if __name__ == "__main__":
    seed()
