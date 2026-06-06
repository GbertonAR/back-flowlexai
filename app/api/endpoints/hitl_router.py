## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: hitl_router.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Endpoints para la gestión de la cola de revisión humana (HITL).
             Permite a los legisladores aprobar o rechazar respuestas de IA.
FECHA CREACIÓN: 2026-03-16
ÚLTIMA MODIFICACIÓN: 2026-03-16
REF. TICKET: #FS-015-HITL
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timezone
from app.db.session import get_session
from app.models.hitl.hitl_review import HITLReview, HITLStatus
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.core.logger import forensic_log as logger

router = APIRouter(prefix="/hitl", tags=["HITL"])

@router.get("/pending", response_model=List[HITLReview])
def get_pending_reviews(
    tenant_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.legislator))
):
    """🌐 [REQ]: Listar revisiones pendientes para una jurisdicción."""
    statement = select(HITLReview).where(
        HITLReview.tenant_id == tenant_id,
        HITLReview.status == HITLStatus.PENDING
    )
    results = session.exec(statement).all()
    return results

@router.post("/{review_id}/approve", response_model=HITLReview)
def approve_review(
    review_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.legislator))
):
    """🌐 [REQ]: Aprobar una respuesta propuesta por la IA."""
    db_review = session.get(HITLReview, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db_review.status = HITLStatus.APPROVED
    db_review.reviewer_id = current_user.id
    db_review.reviewed_at = datetime.now(timezone.utc)
    
    session.add(db_review)
    session.commit()
    session.refresh(db_review)
    
    logger.info(f"✅ [OK] Respuesta HITL APROBADA por {current_user.email} (ID: {review_id})")
    return db_review

@router.post("/{review_id}/reject", response_model=HITLReview)
def reject_review(
    review_id: int,
    notes: str = Body(..., embed=True),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.legislator))
):
    """🌐 [REQ]: Rechazar una respuesta propuesta por la IA con observaciones."""
    db_review = session.get(HITLReview, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db_review.status = HITLStatus.REJECTED
    db_review.reviewer_id = current_user.id
    db_review.reviewer_notes = notes
    db_review.reviewed_at = datetime.now(timezone.utc)
    
    session.add(db_review)
    session.commit()
    session.refresh(db_review)
    
    logger.info(f"❌ [FAULT] Respuesta HITL RECHAZADA por {current_user.email} (ID: {review_id})")
    return db_review
