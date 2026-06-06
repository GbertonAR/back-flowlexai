## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: test_embeddings_real.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script de verificación para probar la conexión real con Azure OpenAI Embeddings.
FECHA CREACIÓN: 2026-03-25
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-011-RAG
"""

import sys
import os

# Añadir el path del backend para poder importar app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.llm import llm_service
from app.core.logger import forensic_log as logger

def test_real_embeddings():
    logger.info("🌐 [REQ] Iniciando prueba de embeddings reales...")
    try:
        texts = ["La ley 26363 crea la Agencia Nacional de Seguridad Vial.", "FlowState AI es innovación."]
        embeddings = llm_service.get_embeddings().embed_documents(texts)
        
        if len(embeddings) == 2 and len(embeddings[0]) == 1536:
            logger.info("✅ [OK] Embeddings generados exitosamente con Azure OpenAI (1536 dims).")
            print("SUCCESS: Embeddings generated correctly.")
        else:
            logger.error(f"❌ [FAULT] Dimensiones inesperadas: {len(embeddings[0]) if embeddings else 'None'}")
            print("FAILURE: Unexpected embedding dimensions.")
            
    except Exception as e:
        logger.error(f"❌ [FAULT] Error crítico en prueba de embeddings: {str(e)}")
        print(f"FAILURE: {str(e)}")

if __name__ == "__main__":
    test_real_embeddings()
