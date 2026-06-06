## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: drafting_router.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Endpoints para la redacción asistida de normativa.
FECHA CREACIÓN: 2026-05-06
ULTIMA MODIFICACIÓN: 2026-05-06
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
import io
from app.modules.assistant.drafting_orchestrator import run_drafting
from app.modules.bias.bias_detector import bias_detector
from app.core.logger import forensic_log as logger
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from sqlmodel import Session
from app.db.session import engine

router = APIRouter(prefix="/drafting", tags=["Redacción AI"])

class DraftingRequest(BaseModel):
    topic: str
    tenant_id: int

@router.post("/generate")
async def generate_draft(
    req: DraftingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    🌐 [REQ] Inicia el flujo de redacción asistida.
    Recupera reglas institucionales del Tenant (Capa 2) y genera el borrador.
    """
    with Session(engine) as session:
        tenant = session.get(Tenant, req.tenant_id)
        if not tenant:
            logger.error(f"❌ [FAULT] Tenant {req.tenant_id} no encontrado para redacción.")
            raise HTTPException(status_code=404, detail="Tenant no encontrado")
        
        rules = tenant.configuration or {}

    try:
        result = await run_drafting(
            tenant_id=req.tenant_id,
            user_id=current_user.id or 1,
            topic=req.topic,
            rules=rules
        )
        return {
            "status": "✅ OK",
            "draft": result["draft"],
            "sources_used": len(result["context"])
        }
    except Exception as e:
        logger.error(f"❌ [FAULT] Error crítico en generación de borrador: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract")
async def extract_text_from_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    🌐 [REQ] Extrae texto de un archivo PDF o DOCX para iniciar un borrador.
    """
    filename = file.filename.lower()
    logger.info(f"🌐 [REQ] Extracción de texto para borrador: '{file.filename}'")
    
    try:
        content = await file.read()
        extracted_text = ""
        
        if filename.endswith(".pdf"):
            from pypdf import PdfReader
            logger.info(f"🧠 [WORKFLOW] Procesando PDF binario...")
            reader = PdfReader(io.BytesIO(content))
            extracted_text = "\n".join([page.extract_text() or "" for page in reader.pages])
            
        elif filename.endswith(".docx"):
            import docx
            logger.info(f"🧠 [WORKFLOW] Procesando DOCX (XML Open Packaging)...")
            doc = docx.Document(io.BytesIO(content))
            extracted_text = "\n".join([para.text for para in doc.paragraphs])
            
        else:
            logger.warning(f"⚠️ [WORKFLOW] Formato no soportado para extracción: {filename}")
            raise HTTPException(status_code=400, detail="Solo se soportan archivos PDF y DOCX.")

        if not extracted_text.strip():
            logger.warning(f"⚠️ [WORKFLOW] El archivo extraído parece estar vacío.")

        logger.info(f"✅ [OK] Extracción finalizada ({len(extracted_text)} caracteres).")
        return {"status": "✅ OK", "text": extracted_text}
        
    except Exception as e:
        logger.error(f"❌ [FAULT] Error en extracción de archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

class AnalysisRequest(BaseModel):
    draft: str

@router.post("/analyze")
async def analyze_impact(
    req: AnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    🧠 [WORKFLOW] Analiza el impacto y sesgo del borrador legislativo.
    WFD Dir 1.4 Compliant.
    """
    logger.info(f"🌐 [REQ] Analizando impacto del borrador (Usuario: {current_user.id})")
    
    if not req.draft.strip():
        logger.warning("⚠️ [WORKFLOW] Intento de análisis sobre borrador vacío.")
        return {
            "status": "PASS",
            "bias_score": 0.0,
            "recommendations": "Borrador vacío. Nada que analizar.",
            "alternatives": [],
            "comparative": {"national": "", "international": ""},
            "legislative_spirit": {"intent": "", "suggestions": []}
        }

    try:
        # Usamos el BiasDetector para auditar el texto
        # query="Análisis de impacto" ya que es una auditoría interna
        analysis = bias_detector.analyze_response(
            query="Auditoría ética de borrador legislativo",
            response=req.draft,
            context=[]
        )
        
        logger.info(f"✅ [OK] Análisis de impacto finalizado. Resultado: {analysis['status']}")
        return analysis
        
    except Exception as e:
        logger.error(f"❌ [FAULT] Error en motor de análisis de impacto: {e}")
        raise HTTPException(status_code=500, detail="Error en el motor de auditoría ética.")
