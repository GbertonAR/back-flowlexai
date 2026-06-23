## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: ingest_service.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Servicio de orquestación para la ingesta de documentos. 
             Vincula archivos físicos con la Ontología Legislativa (Proyecto, Norma).
FECHA CREACIÓN: 2026-05-06
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-ONT-004
"""

import uuid
from sqlmodel import Session, select
from app.db.session import engine
from app.models.expediente import Proyecto, TipoNorma, EstadoExpediente
from app.modules.assistant.vector_store import vector_store
from app.core.logger import forensic_log as logger
from typing import Optional

class IngestService:
    def process_document_ingestion(
        self,
        tenant_id: int,
        user_id: int,
        filename: str,
        content: str,
        tipo_norma_id: int,
        jurisdiccion: str,
        numero_expediente: Optional[str] = None
    ):
        """
        🌐 [REQ] Procesa un documento: crea el Proyecto y lo indexa en RAG con metadata.
        """
        rid = uuid.uuid4().hex[:8]
        logger.info(f"🌐 [REQ] [{rid}] Ingesta iniciada: '{filename}' | tenant={tenant_id} | user={user_id}")

        with Session(engine) as session:

            # ── PASO 1: Verificar TipoNorma ───────────────────────────────────
            logger.info(f"🧠 [WORKFLOW] [{rid}] PASO 1 — Verificando TipoNorma id={tipo_norma_id}")
            try:
                tipo_norma = session.get(TipoNorma, tipo_norma_id)
            except Exception as e:
                logger.error(f"❌ [FAULT] [{rid}] PASO 1 — Error al consultar TipoNorma: {e}")
                raise

            if not tipo_norma:
                logger.error(f"❌ [FAULT] [{rid}] PASO 1 — TipoNorma id={tipo_norma_id} no encontrada. ¿Seed ejecutado?")
                raise ValueError(f"TipoNorma id={tipo_norma_id} no existe. Verificar seed de datos.")
            if tipo_norma.tenant_id != tenant_id:
                logger.error(f"❌ [FAULT] [{rid}] PASO 1 — TipoNorma tenant={tipo_norma.tenant_id} != request tenant={tenant_id}")
                raise ValueError(f"TipoNorma id={tipo_norma_id} no pertenece al Tenant {tenant_id}.")
            logger.info(f"✅ [OK] [{rid}] PASO 1 — TipoNorma '{tipo_norma.nombre}' validada.")

            # ── PASO 2: Metadata de jerarquía normativa ───────────────────────
            logger.info(f"🧠 [WORKFLOW] [{rid}] PASO 2 — Calculando jerarquía normativa")
            try:
                from app.modules.assistant.normative_hierarchy import (
                    get_hierarchy_level, detect_cn_version, is_cn_document, CN_VIGENTE_VERSION
                )
                hierarchy_level = get_hierarchy_level(tipo_norma.nombre)
                logger.info(f"🧠 [WORKFLOW] [{rid}] PASO 2 — Jerarquía: {tipo_norma.nombre} (Nivel {hierarchy_level})")

                cn_version = None
                if is_cn_document(tipo_norma.nombre):
                    cn_version = detect_cn_version(content)
                    if cn_version:
                        status_cn = "VIGENTE" if cn_version == CN_VIGENTE_VERSION else "HISTÓRICA"
                        logger.info(f"🧠 [WORKFLOW] [{rid}] PASO 2 — CN Versión {cn_version} ({status_cn})")
                        if cn_version != CN_VIGENTE_VERSION:
                            logger.warning(f"⚠️ [WORKFLOW] [{rid}] CN versión {cn_version} ≠ vigente {CN_VIGENTE_VERSION}.")
                    else:
                        logger.warning(f"⚠️ [WORKFLOW] [{rid}] No se pudo determinar versión CN para '{filename}'.")
            except Exception as e:
                logger.error(f"❌ [FAULT] [{rid}] PASO 2 — Error en jerarquía normativa: {e}")
                raise

            extra_metadata = {
                "jurisdiccion": jurisdiccion,
                "tipo_norma": tipo_norma.nombre,
                "hierarchy_level": hierarchy_level,
                "vigente": True,
                **({"cn_version": cn_version} if cn_version else {}),
            }

            # ── PASO 3: Indexación vectorial (RAG) ───────────────────────────
            logger.info(f"🧬 [AGENT] [{rid}] PASO 3 — Iniciando indexación vectorial | chars={len(content)}")
            try:
                rag_result = vector_store.ingest_text(
                    tenant_id=str(tenant_id),
                    text=content,
                    source=filename,
                    extra_metadata=extra_metadata
                )
                logger.info(f"✅ [OK] [{rid}] PASO 3 — {rag_result['chunks']} chunks indexados.")
            except Exception as e:
                logger.error(f"❌ [FAULT] [{rid}] PASO 3 — Error en indexación vectorial: {e}")
                raise

            # ── PASO 4: Resolución de Legislador ─────────────────────────────
            logger.info(f"🧠 [WORKFLOW] [{rid}] PASO 4 — Resolviendo Legislador para user_id={user_id}")
            try:
                from app.models.legislative import Legislador
                legislador = session.exec(select(Legislador).where(Legislador.user_id == user_id)).first()
                if not legislador:
                    logger.warning(f"⚠️ [WORKFLOW] [{rid}] PASO 4 — Usuario {user_id} sin Legislador. Creando automático.")
                    legislador = Legislador(user_id=user_id, distrito="Sede Central")
                    session.add(legislador)
                    session.commit()
                    session.refresh(legislador)
                logger.info(f"✅ [OK] [{rid}] PASO 4 — Legislador id={legislador.id} resuelto.")
            except Exception as e:
                logger.error(f"❌ [FAULT] [{rid}] PASO 4 — Error en resolución de Legislador: {e}")
                raise

            # ── PASO 5: Crear Proyecto en DB ─────────────────────────────────
            logger.info(f"🧠 [WORKFLOW] [{rid}] PASO 5 — Creando registro Proyecto en DB")
            try:
                proyecto = Proyecto(
                    numero_expediente=numero_expediente or f"EXP-{rag_result['hash'][:8].upper()}",
                    titulo=filename,
                    texto_completo=content,
                    tenant_id=tenant_id,
                    autor_id=legislador.id,
                    tipo_norma_id=tipo_norma_id,
                    jurisdiccion=jurisdiccion,
                    estado=EstadoExpediente.INGRESO,
                    vigente=True
                )
                session.add(proyecto)
                session.commit()
                session.refresh(proyecto)
                logger.info(f"✅ [OK] [{rid}] PASO 5 — Proyecto id={proyecto.id} creado.")
            except Exception as e:
                logger.error(f"❌ [FAULT] [{rid}] PASO 5 — Error al crear Proyecto: {e}")
                raise

            logger.info(
                f"✅ [OK] [{rid}] Ingesta COMPLETA: '{filename}' | "
                f"Proyecto={proyecto.id} | Legislador={legislador.id} | "
                f"Chunks={rag_result['chunks']} | Artículos={rag_result.get('articles', 0)}"
            )

            return {
                "proyecto_id": proyecto.id,
                "chunks": rag_result["chunks"],
                "articles": rag_result.get("articles", 0),
                "hash": rag_result["hash"],
            }

ingest_service = IngestService()
