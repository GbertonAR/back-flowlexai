## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: config.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Configuración central. Carga datos de .env sin inyectarlos en el 
             sistema operativo para evitar conflictos con ChromaDB. Soporta variables de OS.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-05-19
REF. TICKET: #FS-SEC-CLEAN-LOAD
"""

from pydantic import BaseModel, ConfigDict
import os
from dotenv import dotenv_values

# CARGA LIMPIA: Leemos los archivos a un diccionario, NO al entorno del sistema (os.environ)
# Esto evita que ChromaDB se entere de nuestras variables y falle.
_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_env_path = os.path.join(_base_dir, ".env")
_secret_path = os.path.join(_base_dir, "secret.env")

# Combinamos ambos archivos en un solo diccionario (secret.env tiene prioridad)
env_config = {
    **dotenv_values(_env_path),
    **dotenv_values(_secret_path)
}

def get_config(key: str, default: str = "") -> str:
    """Retorna valor de configuración. os.environ (Azure App Settings) tiene prioridad sobre .env."""
    os_val = os.environ.get(key)
    if os_val is not None and os_val != "":
        return os_val.strip().lstrip('﻿')
    val = env_config.get(key)
    if val is not None and val != "":
        return val.strip().lstrip('﻿')
    return default

class LexIASettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # Usamos get_config para buscar también en os.environ (Cloud Run)
    PROJECT_NAME: str = get_config("PROJECT_NAME", "LexIA SaaS API")
    API_V1_STR: str = get_config("API_V1_STR", "/api/v1")

    # ── Base de Datos ──────────────────────────────────────────────
    POSTGRES_SERVER: str = get_config("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str   = get_config("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = get_config("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str     = get_config("POSTGRES_DB", "flowlex")
    POSTGRES_PORT: str   = get_config("POSTGRES_PORT", "5432")
    ENCRYPTION_KEY: str  = get_config("ENCRYPTION_KEY", "")

    # ── Azure OpenAI ───────────────────────────────────────────────
    # En Azure App Service (WEBSITE_SITE_NAME siempre presente), default a Managed Identity
    USE_MANAGED_IDENTITY: bool = get_config(
        "USE_MANAGED_IDENTITY",
        "true" if os.environ.get("WEBSITE_SITE_NAME") else "false"
    ).lower() == "true"
    OPENAI_API_KEY: str     = get_config("OPENAI_API_KEY", "")
    OPENAI_ENDPOINT: str    = get_config("OPENAI_ENDPOINT", "")
    OPENAI_API_VERSION: str = get_config("OPENAI_API_VERSION", "2024-05-01-preview")
    
    CHAT_DEPLOYMENT: str      = get_config("CHAT_DEPLOYMENT", "gpt-4o")
    EMBEDDING_DEPLOYMENT: str = get_config("EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    # ── JWT / IAM ──────────────────────────────────────────────────
    SECRET_KEY: str = get_config("SECRET_KEY", ENCRYPTION_KEY or "lexia-dev-secret-change-in-prod")
    ALGORITHM: str  = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(get_config("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # ── CORS ───────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list = get_config("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

    # ── Email / Notificaciones ─────────────────────────────────────
    EMAIL_USERNAME: str          = get_config("EMAIL_USERNAME", "")
    EMAIL_PASSWORD: str          = get_config("EMAIL_PASSWORD", "")
    EMAIL_SMTP_HOST: str         = get_config("EMAIL_SMTP_HOST", get_config("EMAIL_SENDER", "smtp.gmail.com"))
    EMAIL_PORT: int              = int(get_config("EMAIL_PORT", "587"))
    EMAIL_NOTIFICATIONS_TO: str  = get_config("EMAIL_NOTIFICATIONS_TO", "gberton1967@gmail.com")

    @property
    def DATABASE_URL(self) -> str:
        if self.POSTGRES_SERVER in ["localhost", "127.0.0.1", ""]:
            # Azure App Service: /home/data persiste entre reinicios
            if os.environ.get("WEBSITE_SITE_NAME"):
                return "sqlite:////home/data/flowstate_dev.db"
            return "sqlite:///flowstate_dev.db"
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = LexIASettings()
