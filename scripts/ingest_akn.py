## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: ingest_akn.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script para ingesta de documentos Akoma Ntoso (XML) en el Vector Store.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-005-GAP5
"""

import os
import sys
from typing import List

# Añadir el path del backend para imports de app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.modules.akn.akn_parser import akn_parser
from app.modules.assistant.vector_store import vector_store
from app.core.logger import forensic_log as logger

def ingest_akn_file(file_path: str, tenant_id: str):
    """Procesa un archivo AKN e indexa su contenido."""
    if not os.path.exists(file_path):
        logger.error(f"❌ [FAULT] Archivo no encontrado: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    logger.info(f"🧬 [AGENT] Procesando documento AKN: {file_path}")
    
    metadata = akn_parser.parse_metadata(content)
    body_text = akn_parser.extract_body_text(content)

    if not body_text:
        logger.warning(f"⚠️ [WORKFLOW] No se extrajo texto del cuerpo en {file_path}")
        return

    # Ingestar en ChromaDB
    # Para simplificar, usamos el FRBRuri como parte del ID y metadatos
    doc_id = metadata.get("frbr_uri", os.path.basename(file_path)).replace("/", "_")
    
    vector_store.add_documents(
        tenant_id=tenant_id,
        texts=[body_text],
        metadatas=[metadata],
        ids=[f"akn_{doc_id}"]
    )
    
    logger.info(f"✅ [OK] Documento AKN indexado: {metadata.get('frbr_uri')}")

if __name__ == "__main__":
    # Ejemplo de uso/test
    # Crear un XML dummy de prueba si no existe
    dummy_akn = """<?xml version="1.0" encoding="UTF-8"?>
    <akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
        <bill>
            <meta>
                <identification source="#lexia">
                    <FRBRWork>
                        <FRBRuri value="/ar/ley/2026/123"/>
                        <FRBRdate date="2026-03-07" name="enactment"/>
                    </FRBRWork>
                </identification>
            </meta>
            <body>
                <section id="sec_1">
                    <num>1.</num>
                    <heading>Artículo de Prueba</heading>
                    <p>Este es un texto legislativo de prueba siguiendo el estándar Akoma Ntoso para LexIA SaaS.</p>
                </section>
            </body>
        </bill>
    </akomaNtoso>
    """
    test_file = "test_akn_doc.xml"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(dummy_akn)
    
    ingest_akn_file(test_file, "999")
    os.remove(test_file)
