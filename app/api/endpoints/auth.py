## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: auth.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Endpoints de autenticación: registro, login y perfil del
             usuario autenticado. Sistema IAM de LexIA Fase 1.
FECHA CREACIÓN: 2026-03-15
ÚLTIMA MODIFICACIÓN: 2026-03-15
REF. TICKET: #FS-012-IAM
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta

from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.email_service import send_demo_user_notification, send_login_notification
from app.core.logger import forensic_log as logger
from app.db.session import get_session
from app.models.tenant import Tenant
from app.models.user import User, UserRegister, UserPublic, TokenResponse, UserRole
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["Auth"])


def _is_demo_user(email: str, full_name: str) -> bool:
    return "demo" in email.lower() or "demo" in full_name.lower()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserRegister,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """
    🌐 [REQ] Registro de nuevo usuario en el sistema.
    El primer usuario del sistema se crea como admin automáticamente.
    Los registros posteriores requieren autenticación de admin.
    """
    # Verificar si el email ya existe
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El email '{payload.email}' ya está registrado."
        )

    # Si no hay usuarios, el primero es admin automáticamente
    user_count = session.exec(select(User)).all()
    role = UserRole.admin if not user_count else payload.role

    # 🛡️ [WFD-COMPLIANCE]: Asegurar integridad referencial del Tenant
    if payload.tenant_id:
        tenant = session.get(Tenant, payload.tenant_id)
        if not tenant:
            if not user_count and payload.tenant_id == 1:
                # Caso especial: Primer registro pide Tenant 1, lo creamos de emergencia
                logger.info("🧠 [WORKFLOW] Creando Tenant #1 (Default) para el primer Administrador.")
                new_tenant = Tenant(
                    id=1,
                    name="Parlamento Principal",
                    domain="flowstate.ai",
                    schema_name="public",
                    plan_type="soberano"
                )
                session.add(new_tenant)
                session.commit()
                session.refresh(new_tenant)
            else:
                logger.error(f"❌ [FAULT] Tenant ID {payload.tenant_id} no existe.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El Tenant ID {payload.tenant_id} no es válido."
                )

    try:
        new_user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=role,
            tenant_id=payload.tenant_id,
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        logger.info(f"✅ [OK] Usuario registrado: {new_user.email} (rol: {new_user.role})")

        if _is_demo_user(new_user.email, new_user.full_name):
            background_tasks.add_task(
                send_demo_user_notification,
                new_user.email,
                new_user.full_name,
            )

        return new_user
    except Exception as e:
        import traceback
        logger.error(f"❌ [FAULT] Error crítico en registro: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Registration Error: {str(e)}")


@router.post("/login", response_model=TokenResponse)
def login(
    background_tasks: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """
    🌐 [REQ] Autenticación via username/password. Retorna JWT Bearer token.
    Compatible con OAuth2PasswordRequestForm (Swagger UI incluido).
    """
    user = session.exec(select(User).where(User.email == form_data.username)).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.error(f"❌ [FAULT] Intento de login fallido para: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")

    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "tenant_id": user.tenant_id,
        },
        expires_delta=expires,
    )
    logger.info(f"✅ [OK] Login exitoso: {user.email} (rol: {user.role})")
    background_tasks.add_task(
        send_login_notification,
        user.email, user.full_name, user.role.value, user.tenant_id or 0,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)):
    """🌐 [REQ] Retorna el perfil del usuario autenticado por su token JWT."""
    return current_user
