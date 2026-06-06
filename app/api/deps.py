## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: deps.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Dependencias de FastAPI para IAM: extracción de usuario del JWT
             y factory de RBAC por rol (require_role).
FECHA CREACIÓN: 2026-03-15
ÚLTIMA MODIFICACIÓN: 2026-03-15
REF. TICKET: #FS-012-IAM
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from typing import List
import jwt

from app.core.security import decode_token
from app.core.logger import forensic_log as logger
from app.db.session import get_session
from app.models.user import User, UserRole

# El tokenUrl apunta al endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """
    🌐 [REQ]: Extrae y valida el usuario autenticado desde el JWT Bearer.
    Requiere un token válido firmado digitalmente.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        raise credentials_exception

    user = session.get(User, int(user_id))
    if not user or not user.is_active:
        logger.error(f"❌ [FAULT] Usuario {user_id} no encontrado o inactivo.")
        raise credentials_exception

    return user


def require_role(*roles: UserRole):
    """
    🛡️ Factory de dependencias RBAC.
    Uso: Depends(require_role(UserRole.admin, UserRole.legislator))
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            logger.error(
                f"❌ [FAULT] Acceso denegado. Usuario {current_user.email} "
                f"tiene rol '{current_user.role}', requiere: {[r.value for r in roles]}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol insuficiente. Roles permitidos: {[r.value for r in roles]}",
            )
        return current_user
    return role_checker
