## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: security.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Capa de seguridad: hashing de contraseñas, generación y
             decodificación de tokens JWT para el sistema IAM de LexIA.
FECHA CREACIÓN: 2026-03-15
ÚLTIMA MODIFICACIÓN: 2026-03-15
REF. TICKET: #FS-012-IAM
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
import jwt
from app.core.config import settings
from app.core.logger import forensic_log as logger

# ── Contexto de hashing (bcrypt) ──────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """🔐 Genera el hash bcrypt de una contraseña en texto plano."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """🔐 Verifica que una contraseña en texto plano coincide con su hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    🧠 [WORKFLOW] Genera un JWT firmado con HS256.
    El payload incluye: sub (user_id), email, role, tenant_id, exp.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info(f"✅ [OK] Token JWT generado para: {data.get('email', 'unknown')}")
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """
    🔐 Decodifica y valida un token JWT.
    Lanza jwt.ExpiredSignatureError o jwt.InvalidTokenError en caso de fallo.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.info(f"✅ [OK] Token decodificado para sub={payload.get('sub')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.error("❌ [FAULT] Token JWT expirado.")
        raise
    except jwt.InvalidTokenError as e:
        logger.error(f"❌ [FAULT] Token JWT inválido: {e}")
        raise
