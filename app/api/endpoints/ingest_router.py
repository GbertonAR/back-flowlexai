## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: ingest_router.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Endpoints REST para la ingesta inteligente y listado de documentos.
             Sincronizado con DocumentsPage.tsx.
FECHA CREACIÓN: 2026-03-15
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-DOCS-FIX
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional, List

from app.modules.assistant.ingest_service import ingest_service
from app.core.logger import forensic_log as logger
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/ingest", tags=["Ingesta Inteligente"])

@router.post("/pdf")
async def ingest_pdf(
    tenant_id: int = Query(...),
    tipo_norma_id: int = Form(1),
    jurisdiccion: str = Form("Nacional"),
    numero_expediente: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.legislator)),
):
    """
    🌐 [REQ] Ingesta un PDF, segmenta por artículo y crea un Proyecto.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF.")

    try:
        from pypdf import PdfReader
        import io

        logger.info(f"🌐 [REQ] Inicio de ingesta PDF: '{file.filename}' (Tenant: {tenant_id})")
        
        raw = await file.read()
        reader = PdfReader(io.BytesIO(raw))
        
        page_count = len(reader.pages)
        logger.info(f"🧠 [WORKFLOW] PDF cargado: {page_count} páginas detectadas.")
        
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        
        if not full_text.strip():
            logger.warning(f"⚠️ [WORKFLOW] El PDF '{file.filename}' parece estar vacío o es una imagen sin OCR.")

        result = ingest_service.process_document_ingestion(
            tenant_id=tenant_id,
            user_id=current_user.id or 1,
            filename=file.filename,
            content=full_text,
            tipo_norma_id=tipo_norma_id,
            jurisdiccion=jurisdiccion,
            numero_expediente=numero_expediente,
        )

        logger.info(f"✅ [OK] Ingesta exitosa: {result['chunks']} chunks creados.")

        return {
            "status": "✅ OK",
            "proyecto_id": result["proyecto_id"],
            "hash": result["hash"],
            "chunks_indexed": result["chunks"],
            "articles_found": result.get("articles", 0),
        }
    except ImportError:
        msg = "❌ [FAULT] Error crítico: pypdf no está instalado en el servidor."
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        logger.error(f"❌ [FAULT] Error en ingesta PDF '{file.filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xml")
async def ingest_xml(
    tenant_id: int = Query(...),
    tipo_norma_id: int = Form(1),
    jurisdiccion: str = Form("Nacional"),
    numero_expediente: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.legislator)),
):
    """
    🌐 [REQ] Ingesta un documento AKN XML (ISO 36000), extrae artículos y los indexa en RAG.
    Compatible con exportaciones HORUS, SIL y cualquier fuente Akoma Ntoso.
    """
    if not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos XML (Akoma Ntoso).")

    try:
        raw = await file.read()
        xml_text = raw.decode("utf-8", errors="replace")

        result = ingest_service.process_document_ingestion(
            tenant_id=tenant_id,
            user_id=current_user.id or 1,
            filename=file.filename,
            content=xml_text,
            tipo_norma_id=tipo_norma_id,
            jurisdiccion=jurisdiccion,
            numero_expediente=numero_expediente,
        )

        return {
            "status": "✅ OK",
            "formato": "AKN XML",
            "proyecto_id": result["proyecto_id"],
            "hash": result["hash"],
            "chunks_indexed": result["chunks"],
            "articles_found": result.get("articles", 0),
        }
    except Exception as e:
        logger.error(f"❌ [FAULT] Error en ingesta XML: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list/{tenant_id}")
async def list_documents(tenant_id: int):
    """
    🌐 [REQ] Lista todos los documentos indexados para un Tenant.
    """
    try:
        from app.modules.assistant.vector_store import vector_store
        docs = vector_store.get_all_documents(tenant_id)
        return {"documents": docs}
    except Exception as e:
        logger.error(f"❌ [FAULT] Error al listar documentos: {e}")
        return {"documents": []}

@router.delete("/document/{tenant_id}")
async def delete_document(tenant_id: int, source_name: str):
    """🌐 [REQ] Elimina un documento y sus vectores."""
    from app.modules.assistant.vector_store import vector_store
    success = vector_store.delete_document(tenant_id, source_name)
    if not success:
        raise HTTPException(status_code=500, detail="Error al eliminar el documento.")
    return {"status": "🗑️ Documento eliminado"}

@router.patch("/document/{tenant_id}")
async def update_document(tenant_id: int, source_name: str, meta: dict):
    """🌐 [REQ] Actualiza metadatos (jurisdicción, jerarquía) de un documento."""
    from app.modules.assistant.vector_store import vector_store
    success = vector_store.update_document_metadata(tenant_id, source_name, meta)
    if not success:
        raise HTTPException(status_code=500, detail="Error al actualizar metadatos.")
    return {"status": "✅ Metadatos actualizados"}

@router.get("/status/{tenant_id}")
async def get_status(tenant_id: int):
    from app.modules.assistant.vector_store import vector_store
    count = vector_store.get_document_count(str(tenant_id))
    return {"tenant_id": tenant_id, "indexed_chunks": count}
