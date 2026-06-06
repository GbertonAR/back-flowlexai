"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: reset_and_reingest.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script de utilidad para limpiar la ChromaDB contaminada con
             vectores cero (fallback de rate limit 429) y re-ingestar todos
             los documentos legislativos con embeddings reales.
             EJECUTAR CON EL BACKEND DETENIDO.
FECHA CREACIÓN: 2026-05-12
ÚLTIMA MODIFICACIÓN: 2026-05-12
REF. TICKET: #FS-011-RAG
"""

import os
import sys
import shutil
import time

# Asegurar que el path raíz del backend esté en sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

CHROMA_DIR = os.path.join(BACKEND_DIR, "chroma_db")
TENANT_ID = "1"  # Tenant principal de desarrollo

PDF_SOURCES = [
    os.path.join(BACKEND_DIR, "..", "Archivos", "constitucionargentina.pdf"),
    os.path.join(BACKEND_DIR, "..", "..", "..", "Documentos", "FlowLexAI", "DataRAG", "CABA-Contitucion.pdf"),
    os.path.join(BACKEND_DIR, "..", "..", "..", "Documentos", "FlowLexAI", "DataRAG", "BUENOS-AIRES Contitu.pdf"),
    os.path.join(BACKEND_DIR, "..", "..", "..", "Documentos", "FlowLexAI", "DataRAG", "TUCUMAN conti.pdf"),
    os.path.join(BACKEND_DIR, "..", "..", "..", "Documentos", "FlowLexAI", "DataRAG", "reglamentoDiputados.pdf"),
    os.path.join(BACKEND_DIR, "..", "..", "..", "Documentos", "FlowLexAI", "DataRAG", "reglamentoSenado.pdf"),
    os.path.join(BACKEND_DIR, "..", "..", "..", "Documentos", "FlowLexAI", "DataRAG", "Reglamento2023Legislatura.pdf"),
]


def step1_clean_chromadb():
    print("\n" + "="*60)
    print("🧹 PASO 1 — Limpieza de ChromaDB contaminada")
    print("="*60)

    if not os.path.exists(CHROMA_DIR):
        print(f"  ⚠️  Directorio no encontrado: {CHROMA_DIR}. Se creará en el paso 2.")
        return

    shutil.rmtree(CHROMA_DIR)
    os.makedirs(CHROMA_DIR, exist_ok=True)
    print(f"  ✅ ChromaDB limpiada: {CHROMA_DIR}")


def step2_reingest_pdfs():
    print("\n" + "="*60)
    print("📥 PASO 2 — Re-ingesta de documentos legislativos")
    print("="*60)

    from app.modules.assistant.vector_store import vector_store
    from app.core.llm import DeterministicMockEmbedding

    # Verificar modo embedding
    is_real = vector_store.embedder.is_real
    mode = "REAL (Azure OpenAI)" if is_real else "⚠️ MOCK (sin credenciales)"
    print(f"\n  Modo de embeddings: {mode}")
    if not is_real:
        print("  ❌ Las credenciales de Azure OpenAI no están activas.")
        print("     Verificá OPENAI_API_KEY y OPENAI_ENDPOINT en .env")
        sys.exit(1)

    total_ok = 0
    total_fail = 0

    for pdf_path in PDF_SOURCES:
        pdf_path = os.path.normpath(pdf_path)
        name = os.path.basename(pdf_path)

        if not os.path.exists(pdf_path):
            print(f"\n  ⚠️  No encontrado (skip): {pdf_path}")
            total_fail += 1
            continue

        print(f"\n  📄 Ingestando: {name}")
        try:
            chunks = vector_store.ingest_pdf(
                tenant_id=TENANT_ID,
                file_path=pdf_path,
                source_name=name,
            )
            print(f"     ✅ {chunks} fragmentos indexados.")
            total_ok += 1
            time.sleep(2)  # Pausa extra entre PDFs para respetar TPM
        except Exception as e:
            print(f"     ❌ Error: {e}")
            total_fail += 1

    return total_ok, total_fail


def step3_verify():
    print("\n" + "="*60)
    print("🔍 PASO 3 — Verificación de búsqueda semántica")
    print("="*60)

    from app.modules.assistant.vector_store import vector_store

    count = vector_store.get_document_count(TENANT_ID)
    print(f"\n  Total de fragmentos indexados para Tenant {TENANT_ID}: {count}")

    test_query = "¿Cuáles son los derechos fundamentales que garantiza la Constitución?"
    print(f"\n  Query de prueba: \"{test_query}\"")
    results = vector_store.query(TENANT_ID, test_query, n_results=3)
    docs = results.get("documents", [[]])[0]

    if docs and any(len(d) > 50 for d in docs):
        print(f"\n  ✅ Búsqueda semántica operativa. Fragmentos recuperados: {len(docs)}")
        for i, doc in enumerate(docs[:2]):
            print(f"\n  [{i+1}] {doc[:200]}...")
    else:
        print("\n  ❌ La búsqueda no retornó resultados útiles.")


if __name__ == "__main__":
    print("\n🚀 LexIA — Reset y Re-ingesta de Corpus Legislativo")
    print(f"   Backend dir : {BACKEND_DIR}")
    print(f"   ChromaDB    : {CHROMA_DIR}")
    print(f"   Tenant ID   : {TENANT_ID}")
    print(f"   PDFs fuente : {len(PDF_SOURCES)} archivos")

    step1_clean_chromadb()
    ok, fail = step2_reingest_pdfs()

    print("\n" + "="*60)
    print(f"  PDFs procesados: ✅ {ok} OK  |  ❌ {fail} fallos")
    print("="*60)

    if ok > 0:
        step3_verify()

    print("\n✅ Script finalizado. Podés reiniciar el backend.\n")
