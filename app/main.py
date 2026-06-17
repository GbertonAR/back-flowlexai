## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: main.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Entrypoint principal de la API FastAPI para el core de LexIA.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-FIN-001
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import forensic_log as logger
from app.core.health import health_monitor

from app.api.endpoints import (
    tenants, auditoria, auth, ingest_router, 
    hitl_router, subscriptions, compare_router, 
    metrics_router, drafting_router
)
from app.modules.assistant import router as assistant_router
from app.modules.external import router as external_router
from app import models # Importar modelos para registro de metadatos (FKs)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("✅ [OK] LexIA Core Engine Iniciado correctamente. Inicializando SQLite local...")
    try:
        from sqlmodel import SQLModel
        from app.db.session import engine
        SQLModel.metadata.create_all(engine)
        from scripts.seed_test_users import seed
        seed()
        logger.info("✅ [OK] Seed de usuarios de prueba completado (admin, legislator, analyst, readonly).")
    except Exception as e:
        logger.error(f"❌ [FAULT] Error en el seed de Base de Datos: {e}")
    await health_monitor.run_full_diagnostic()
    yield

app = FastAPI(
    title="LexIA Core API",
    description="Soberano engine for neural legislative orchestration.",
    version="1.2.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Registrando Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(ingest_router.router, prefix=settings.API_V1_STR)
app.include_router(drafting_router.router, prefix=settings.API_V1_STR)
app.include_router(tenants.router, prefix=settings.API_V1_STR)
app.include_router(auditoria.router, prefix=settings.API_V1_STR)
app.include_router(hitl_router.router, prefix=settings.API_V1_STR)
app.include_router(metrics_router.router, prefix=settings.API_V1_STR)
app.include_router(subscriptions.router, prefix=settings.API_V1_STR, tags=["Subscriptions"])
app.include_router(compare_router.router, prefix=settings.API_V1_STR, tags=["Comparison"])
app.include_router(external_router.router, prefix=settings.API_V1_STR, tags=["External"])
app.include_router(assistant_router.router, prefix=settings.API_V1_STR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "LexIA Core API - FlowState AI", "status": "✅ [OK] Operativo"}

@app.get("/api/v1/health")
async def get_health():
    return health_monitor.status
