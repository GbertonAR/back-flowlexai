"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: seed_and_ingest_rag.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Siembra tipos de norma y luego ingesta todos los PDFs del
             directorio DataRAG al vector store FAISS para el tenant 1.
             Ejecutar desde backend/ con: poetry run python scripts/seed_and_ingest_rag.py
FECHA CREACIÓN: 2026-06-02
REF. TICKET: #FS-RAG-SEED-001
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db.session import engine
from app.models.expediente import TipoNorma
from app.modules.assistant.ingest_service import ingest_service
from app.core.logger import forensic_log as logger

TENANT_ID = 1

TIPOS_NORMA = [
    {"id": 1,  "nombre": "Constitución", "nivel_jerarquico": 1, "tenant_id": TENANT_ID},
    {"id": 2,  "nombre": "Ley",          "nivel_jerarquico": 3, "tenant_id": TENANT_ID},
    {"id": 3,  "nombre": "Decreto",      "nivel_jerarquico": 4, "tenant_id": TENANT_ID},
    {"id": 4,  "nombre": "Reglamento",   "nivel_jerarquico": 4, "tenant_id": TENANT_ID},
    {"id": 5,  "nombre": "Resolución",   "nivel_jerarquico": 5, "tenant_id": TENANT_ID},
    {"id": 6,  "nombre": "Ordenanza",    "nivel_jerarquico": 4, "tenant_id": TENANT_ID},
]

PDF_DIR = r"C:\GBerton2026\Documentos\FlowLexAI\DataRAG"

DOCUMENTOS = [
    {"file": "CABA-Contitucion.pdf",          "jurisdiccion": "CABA",          "tipo_id": 1},
    {"file": "BUENOS-AIRES Contitu.pdf",       "jurisdiccion": "Buenos Aires",  "tipo_id": 1},
    {"file": "TUCUMAN conti.pdf",              "jurisdiccion": "Tucumán",       "tipo_id": 1},
    {"file": "reglamentoDiputados.pdf",        "jurisdiccion": "Nacional",      "tipo_id": 4},
    {"file": "reglamentoSenado.pdf",           "jurisdiccion": "Nacional",      "tipo_id": 4},
    {"file": "Reglamento2023Legislatura.pdf",  "jurisdiccion": "Nacional",      "tipo_id": 4},
    {"file": "hoja2.pdf",                      "jurisdiccion": "Nacional",      "tipo_id": 2},
    {"file": "3.pdf",                          "jurisdiccion": "Nacional",      "tipo_id": 2},
]


def seed_tipos_norma():
    with Session(engine) as session:
        created = 0
        for t in TIPOS_NORMA:
            existing = session.get(TipoNorma, t["id"])
            if not existing:
                session.add(TipoNorma(**t))
                created += 1
        session.commit()
    logger.info(f"✅ [OK] TipoNorma: {created} nuevos registros creados.")


def ingest_pdfs():
    from pypdf import PdfReader

    ok, failed = 0, 0
    for doc in DOCUMENTOS:
        path = os.path.join(PDF_DIR, doc["file"])
        if not os.path.exists(path):
            logger.warning(f"⚠️ Archivo no encontrado, saltando: {path}")
            continue

        try:
            logger.info(f"🌐 [REQ] Ingesta: {doc['file']} | {doc['jurisdiccion']}")
            reader = PdfReader(path)
            text = "\n".join(p.extract_text() or "" for p in reader.pages)

            if not text.strip():
                logger.warning(f"⚠️ PDF sin texto extraíble (posible imagen): {doc['file']}")

            result = ingest_service.process_document_ingestion(
                tenant_id=TENANT_ID,
                user_id=1,
                filename=doc["file"],
                content=text,
                tipo_norma_id=doc["tipo_id"],
                jurisdiccion=doc["jurisdiccion"],
            )
            logger.info(f"✅ [OK] {doc['file']} → {result['chunks']} chunks | proyecto_id={result['proyecto_id']}")
            ok += 1
        except Exception as e:
            logger.error(f"❌ [FAULT] Error ingesta {doc['file']}: {e}")
            failed += 1

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Ingesta completada: {ok} exitosos | {failed} fallidos")


if __name__ == "__main__":
    logger.info("🧬 [AGENT] Iniciando seed de TipoNorma + ingesta RAG...")
    seed_tipos_norma()
    ingest_pdfs()
