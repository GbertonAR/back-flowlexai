## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: health.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Servicio de Watchdog para diagnóstico proactivo de infraestructura y nube.
              Valida conectividad con Azure OpenAI, PostgreSQL y persistencia local.
FECHA CREACIÓN: 2026-04-29
ÚLTIMA MODIFICACIÓN: 2026-04-29
REF. TICKET: #FS-030-HEALTH
"""

import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any
from app.core.config import settings
from app.core.logger import forensic_log as logger
from app.db.session import engine
from sqlmodel import text

class HealthService:
    def __init__(self):
        self.status = {
            "is_alive": False,
            "last_check": None,
            "mode": "STARTING", # STARTING, SOBERANO (Degraded), FULL
            "services": {
                "database": False,
                "azure_embeddings": False,
                "openai_llm": False,
                "chroma_persistence": False
            }
        }

    async def check_db(self) -> bool:
        """Valida conexión con PostgreSQL/SQLite."""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"❌ [FAULT] Health: DB Unreachable - {str(e)}")
            return False

    async def check_azure_connectivity(self) -> bool:
        """Ping ligero al endpoint de Azure OpenAI."""
        if not settings.OPENAI_ENDPOINT or not settings.OPENAI_API_KEY:
            return False
            
        try:
            # Construir URL de validación (usamos el endpoint base)
            url = f"{settings.OPENAI_ENDPOINT}/openai/deployments?api-version={settings.OPENAI_API_VERSION}"
            headers = {"api-key": settings.OPENAI_API_KEY}
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=5.0)
                # 401/404/403 de Azure son "conectividad OK" (el host respondió)
                # Pero un timeout o NameResolutionError son fallos de red.
                return resp.status_code < 500
        except Exception:
            return False

    async def check_storage(self) -> bool:
        """Verifica que la tabla de vectores es accesible en la BD (reemplaza check FAISS en disco)."""
        try:
            from sqlmodel import Session, text as sa_text
            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1 FROM documentchunk LIMIT 1"))
            return True
        except Exception:
            # La tabla puede estar vacía; si la consulta falla por tabla inexistente, retorna False
            return False

    async def run_full_diagnostic(self):
        """Ejecuta el checklist completo de salud."""
        logger.info("🔍 [HEALTH] Iniciando diagnóstico proactivo de entorno...")
        
        results = {
            "database": await self.check_db(),
            "azure_cloud": await self.check_azure_connectivity(),
            "chroma_persistence": await self.check_storage()
        }
        
        self.status["services"] = results
        self.status["is_alive"] = results["database"] # DB es crítica
        self.status["last_check"] = datetime.now().isoformat()
        self.status["last_check_time"] = datetime.now()
        
        if not results["azure_cloud"]:
            self.status["mode"] = "SOBERANO (Offline)"
            logger.warning("⚠️ [ALERT] Entorno NUBE degradado. Activando MODO SOBERANO (IA Mocks).")
        elif all(results.values()):
            self.status["mode"] = "FULL (Operativo)"
            logger.info("✅ [OK] Entorno 100% operativo y conectado.")
        else:
            self.status["mode"] = "DEGRADADO"

        return self.status

# Instancia global (Singleton)
health_monitor = HealthService()
