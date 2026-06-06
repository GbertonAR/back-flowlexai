## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: subscriptions.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Endpoints para la gestión de suscripciones a alertas legislativas.
FECHA CREACIÓN: 2026-03-25
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-020-ALERTS
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.db.session import engine
from app.models.subscription import Subscription
from app.api.deps import get_current_user
from app.models.user import User
from app.core.logger import forensic_log as logger

router = APIRouter()

@router.post("/", response_model=Subscription)
async def create_subscription(
    subscription_data: Subscription,
    current_user: User = Depends(get_current_user)
):
    """🌐 [REQ] Crea una nueva suscripción temática."""
    logger.info(f"🌐 [REQ] Creando suscripción para usuario {current_user.id} en tenant {current_user.tenant_id}")
    
    with Session(engine) as session:
        # Asegurar tenant_id y user_id del contexto de seguridad
        subscription_data.tenant_id = current_user.tenant_id
        subscription_data.user_id = current_user.id
        
        session.add(subscription_data)
        session.commit()
        session.refresh(subscription_data)
        
        logger.info(f"✅ [OK] Suscripción {subscription_data.id} creada exitosamente.")
        return subscription_data

@router.get("/", response_model=List[Subscription])
async def list_subscriptions(
    current_user: User = Depends(get_current_user)
):
    """🌐 [REQ] Lista las suscripciones activas del usuario."""
    with Session(engine) as session:
        statement = select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.tenant_id == current_user.tenant_id
        )
        results = session.exec(statement).all()
        return results

@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user)
):
    """🌐 [REQ] Elimina una suscripción."""
    with Session(engine) as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription or subscription.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Suscripción no encontrada")
        
        session.delete(subscription)
        session.commit()
        logger.info(f"✅ [OK] Suscripción {subscription_id} eliminada.")
        return {"status": "deleted"}
