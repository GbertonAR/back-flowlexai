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
        with Session(engine) as session:
            # 1. Verificar Tipo de Norma
            tipo_norma = session.get(TipoNorma, tipo_norma_id)
            if not tipo_norma or tipo_norma.tenant_id != tenant_id:
                raise ValueError("Tipo de Norma no válido para este Tenant.")

            # 2. Ingestar en Vector Store (RAG)
            from app.modules.assistant.normative_hierarchy import (
                get_hierarchy_level, detect_cn_version, is_cn_document, CN_VIGENTE_VERSION
            )
            hierarchy_level = get_hierarchy_level(tipo_norma.nombre)
            logger.info(f"🧠 [WORKFLOW] Jerarquía detectada: {tipo_norma.nombre} (Nivel {hierarchy_level})")

            # Control de versiones CN: detectar automáticamente si es texto 1853/1994
            cn_version = None
            if is_cn_document(tipo_norma.nombre):
                cn_version = detect_cn_version(content)
                if cn_version:
                    status_cn = "VIGENTE" if cn_version == CN_VIGENTE_VERSION else "HISTÓRICA"
                    logger.info(f"🧠 [WORKFLOW] CN Detectada: Versión {cn_version} ({status_cn})")
                    if cn_version != CN_VIGENTE_VERSION:
                        logger.warning(
                            f"⚠️ [WORKFLOW] CN versión {cn_version} detectada en '{filename}'. "
                            f"El texto vigente es {CN_VIGENTE_VERSION}. "
                            f"El reranker penalizará este documento en consultas generales."
                        )
                else:
                    logger.warning(f"⚠️ [WORKFLOW] No se pudo determinar la versión de la CN para '{filename}'.")

            extra_metadata = {
                "jurisdiccion": jurisdiccion,
                "tipo_norma": tipo_norma.nombre,
                "hierarchy_level": hierarchy_level,
                "vigente": True,
                **({"cn_version": cn_version} if cn_version else {}),
            }
            
            logger.info(f"🧬 [AGENT] Iniciando indexación vectorial en FAISS...")
            rag_result = vector_store.ingest_text(
                tenant_id=str(tenant_id),
                text=content,
                source=filename,
                extra_metadata=extra_metadata
            )

            # 3. Vincular con Legislador (Autor)
            from app.models.legislative import Legislador
            logger.info(f"🧠 [WORKFLOW] Validando registro de Legislador para Usuario ID {user_id}...")
            legislador = session.exec(select(Legislador).where(Legislador.user_id == user_id)).first()
            
            if not legislador:
                # Si no existe el legislador para este usuario (ej: es admin), creamos uno genérico
                logger.warning(f"⚠️ [WORKFLOW] Usuario ID {user_id} no tiene registro de Legislador. Creando uno automático...")
                legislador = Legislador(user_id=user_id, tenant_id=tenant_id, distrito="Sede Central")
                session.add(legislador)
                session.commit()
                session.refresh(legislador)

            # 4. Crear Registro de Proyecto en DB (Capa 1)
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
            
            logger.info(
                f"✅ [OK] Documento '{filename}' persistido en DB y RAG. "
                f"Proyecto ID: {proyecto.id} (Autor Legislador: {legislador.id}). "
                f"Chunks: {rag_result['chunks']} ({rag_result.get('articles', 0)} artículos)."
            )

            return {
                "proyecto_id": proyecto.id,
                "chunks": rag_result["chunks"],
                "articles": rag_result.get("articles", 0),
                "hash": rag_result["hash"],
            }

ingest_service = IngestService()
