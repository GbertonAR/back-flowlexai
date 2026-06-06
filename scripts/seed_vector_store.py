## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: seed_vector_store.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script para poblar la base de datos vectorial ChromaDB con el conocimiento base de LexIA.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-006-SEED
"""

import os
import sys
from typing import List

# Añadir el path del backend para poder importar modulos de app
sys.path.append(os.path.join(os.getcwd()))

from app.modules.assistant.vector_store import vector_store
from app.core.logger import forensic_log as logger

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Divide un texto en fragmentos con solapamiento."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def seed():
    logger.info("🧬 [AGENT] Iniciando proceso de seeding para Vector Store.")
    
    file_path = "../extracted_docx_utf8.txt"
    if not os.path.exists(file_path):
        logger.error(f"❌ [FAULT] Archivo de origen no encontrado: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Procesamiento simple de fragmentación
    chunks = chunk_text(content)
    
    tenant_id = "999"  # Tenant del sistema para conocimiento base
    texts = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        texts.append(chunk)
        metadatas.append({"source": "LexIA_Design_Doc", "type": "base_knowledge"})
        ids.append(f"lexia_base_{i}")

    try:
        vector_store.add_documents(tenant_id, texts, metadatas, ids)
        logger.info(f"✅ [OK] Seeding completado. {len(texts)} fragmentos indexados en Tenant {tenant_id}.")
    except Exception as e:
        logger.error(f"❌ [FAULT] Error durante el seeding: {e}")

if __name__ == "__main__":
    seed()
