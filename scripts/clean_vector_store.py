## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: clean_vector_store.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script para resetear la colección de ChromaDB y eliminar datos de prueba.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-008-CLEAN
"""

import chromadb
import os
from app.core.logger import forensic_log as logger

def clean_store():
    persist_directory = "./chroma_db"
    if not os.path.exists(persist_directory):
        logger.warning("⚠️ [WORKFLOW] No se encontró el directorio de ChromaDB.")
        return

    client = chromadb.PersistentClient(path=persist_directory)
    
    try:
        # Intentar eliminar la colección de LexIA
        client.delete_collection("lexia_knowledge")
        logger.info("✅ [OK] Colección 'lexia_knowledge' eliminada con éxito.")
    except Exception as e:
        logger.error(f"❌ [FAULT] Error al eliminar colección: {str(e)}")

if __name__ == "__main__":
    clean_store()
