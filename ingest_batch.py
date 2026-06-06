"""Ingesta batch de los 6 PDFs al tenant 1 con metadata completa."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from pypdf import PdfReader
from app.modules.assistant.vector_store import vector_store
from app.modules.assistant.normative_hierarchy import (
    get_hierarchy_level, detect_cn_version, is_cn_document,
    CN_VIGENTE_VERSION,
)

TENANT_ID = "1"

PDFS = [
    {
        "path": r"C:\GBerton2026\Documentos\FlowLexAI\DataRAG\CABA-Contitucion.pdf",
        "source": "CABA-Constitucion.pdf",
        "jurisdiccion": "CABA",
        "tipo_norma": "Constitucion Provincial",
    },
    {
        "path": r"C:\GBerton2026\Documentos\FlowLexAI\DataRAG\BUENOS-AIRES Contitu.pdf",
        "source": "BuenosAires-Constitucion.pdf",
        "jurisdiccion": "Buenos Aires",
        "tipo_norma": "Constitucion Provincial",
    },
    {
        "path": r"C:\GBerton2026\Documentos\FlowLexAI\DataRAG\TUCUMAN conti.pdf",
        "source": "Tucuman-Constitucion.pdf",
        "jurisdiccion": "Tucuman",
        "tipo_norma": "Constitucion Provincial",
    },
    {
        "path": r"C:\GBerton2026\Documentos\FlowLexAI\DataRAG\reglamentoDiputados.pdf",
        "source": "ReglamentoDiputados.pdf",
        "jurisdiccion": "Nacional",
        "tipo_norma": "Reglamento",
    },
    {
        "path": r"C:\GBerton2026\Documentos\FlowLexAI\DataRAG\reglamentoSenado.pdf",
        "source": "ReglamentoSenado.pdf",
        "jurisdiccion": "Nacional",
        "tipo_norma": "Reglamento",
    },
    {
        "path": r"C:\GBerton2026\Documentos\FlowLexAI\DataRAG\Reglamento2023Legislatura.pdf",
        "source": "Reglamento2023Legislatura.pdf",
        "jurisdiccion": "Nacional",
        "tipo_norma": "Reglamento",
    },
]

total_chunks = 0
total_articles = 0
t0_global = time.time()

for i, doc in enumerate(PDFS, 1):
    path = doc["path"]
    if not os.path.exists(path):
        print(f"[{i}/6] SKIP - no encontrado: {path}")
        continue

    print(f"\n[{i}/6] {doc['source']}")
    t0 = time.time()

    reader = PdfReader(path)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    print(f"       Paginas: {len(reader.pages)} | Chars: {len(full_text)}")

    # Metadata con jerarquia y control de version CN
    tipo_norma = doc["tipo_norma"]
    hierarchy_level = get_hierarchy_level(tipo_norma)
    extra_metadata = {
        "jurisdiccion": doc["jurisdiccion"],
        "tipo_norma": tipo_norma,
        "hierarchy_level": hierarchy_level,
        "vigente": True,
    }
    if is_cn_document(tipo_norma):
        cn_ver = detect_cn_version(full_text)
        if cn_ver:
            extra_metadata["cn_version"] = cn_ver
            flag = "(VIGENTE)" if cn_ver == CN_VIGENTE_VERSION else f"(HISTORICA - no vigente)"
            print(f"       CN version detectada: {cn_ver} {flag}")

    print(f"       Jerarquia: nivel {hierarchy_level} ({tipo_norma})")

    result = vector_store.ingest_text(
        tenant_id=TENANT_ID,
        text=full_text,
        source=doc["source"],
        extra_metadata=extra_metadata,
    )

    elapsed = time.time() - t0
    total_chunks += result["chunks"]
    total_articles += result.get("articles", 0)
    print(f"       Chunks: {result['chunks']} | Arts: {result.get('articles',0)} | {elapsed:.1f}s")

elapsed_global = time.time() - t0_global
count = vector_store.get_document_count(TENANT_ID)

print(f"\n{'='*40}")
print(f"INGESTA COMPLETADA")
print(f"  Documentos : 6")
print(f"  Chunks     : {total_chunks}")
print(f"  Articulos  : {total_articles}")
print(f"  En ChromaDB (tenant 1): {count}")
print(f"  Tiempo     : {elapsed_global:.1f}s")
