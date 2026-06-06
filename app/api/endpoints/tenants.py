## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: tenants.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Endpoints CRUD para la gestión de jurisidcciones (Tenants) en el modelo B2G.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-001
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List
from app.db.session import get_session
from app.models.tenant import Tenant, TenantBase
from app.core.logger import forensic_log as logger
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/tenants", tags=["Tenants"])

@router.post("/", response_model=Tenant, status_code=201)
def create_tenant(
    tenant: TenantBase, 
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.admin))
):
    """🌐 [REQ]: Crear nuevo parlamento/jurisdicción."""
    db_tenant = Tenant.model_validate(tenant)
    session.add(db_tenant)
    session.commit()
    session.refresh(db_tenant)
    logger.info(f"✅ [OK] Tenant creado: {db_tenant.name} (ID: {db_tenant.id})")
    return db_tenant

@router.get("/", response_model=List[Tenant])
def read_tenants(
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """🌐 [REQ]: Listar parlamentos activos."""
    tenants = session.exec(select(Tenant).offset(offset).limit(limit)).all()
    return tenants

@router.get("/{tenant_id}", response_model=Tenant)
def read_tenant(tenant_id: int, session: Session = Depends(get_session)):
    """🌐 [REQ]: Obtener detalles de un parlamento específico."""
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        logger.error(f"❌ [FAULT] Tenant no encontrado: {tenant_id}")
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
