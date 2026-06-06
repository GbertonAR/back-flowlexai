"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: ingest_gcp.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Ingesta los PDFs del directorio DataRAG en el backend
             desplegado en GCP Cloud Run via API REST.
             Ejecutar: poetry run python scripts/ingest_gcp.py
FECHA CREACIÓN: 2026-06-02
REF. TICKET: #FS-RAG-GCP-001
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from app.core.logger import forensic_log as logger

GCP_BASE     = "https://lexia-backend-222680624860.us-central1.run.app/api/v1"
ADMIN_EMAIL  = "admin@flowlex.ai"
ADMIN_PASS   = "admin"
TENANT_ID    = 1
PDF_DIR      = r"C:\GBerton2026\Documentos\FlowLexAI\DataRAG"

DOCUMENTOS = [
    {"file": "Reglamento2023Legislatura.pdf", "jurisdiccion": "Nacional", "tipo_norma_id": 4},
]


def get_token(client: httpx.Client) -> str:
    r = client.post(f"{GCP_BASE}/auth/login",
                    data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
    r.raise_for_status()
    token = r.json()["access_token"]
    logger.info(f"✅ [OK] Token GCP obtenido para {ADMIN_EMAIL}")
    return token


def seed_tipos_norma(client: httpx.Client, token: str):
    """Registra los tipos de norma en GCP via endpoint de admin."""
    tipos = [
        {"nombre": "Constitución", "nivel_jerarquico": 1},
        {"nombre": "Ley",          "nivel_jerarquico": 3},
        {"nombre": "Decreto",      "nivel_jerarquico": 4},
        {"nombre": "Reglamento",   "nivel_jerarquico": 4},
        {"nombre": "Resolución",   "nivel_jerarquico": 5},
        {"nombre": "Ordenanza",    "nivel_jerarquico": 4},
    ]
    headers = {"Authorization": f"Bearer {token}"}
    created = 0
    for t in tipos:
        try:
            r = client.post(f"{GCP_BASE}/tenants/1/tipos-norma",
                            headers=headers, json=t, timeout=10)
            if r.status_code in (200, 201):
                created += 1
        except Exception:
            pass

    if created:
        logger.info(f"✅ [OK] TipoNorma: {created} registros creados en GCP.")
    else:
        logger.info("🧠 [WORKFLOW] TipoNorma: ya existen o endpoint no disponible — continuando.")


def ingest_pdf(client: httpx.Client, token: str, doc: dict) -> dict:
    path = os.path.join(PDF_DIR, doc["file"])
    if not os.path.exists(path):
        logger.warning(f"⚠️ Archivo no encontrado: {path}")
        return {"ok": False, "error": "not found"}

    headers = {"Authorization": f"Bearer {token}"}
    params  = {"tenant_id": TENANT_ID}
    data    = {"jurisdiccion": doc["jurisdiccion"], "tipo_norma_id": doc["tipo_norma_id"]}

    with open(path, "rb") as f:
        files = {"file": (doc["file"], f, "application/pdf")}
        r = client.post(f"{GCP_BASE}/ingest/pdf",
                        headers=headers, params=params,
                        data=data, files=files,
                        timeout=660.0)

    if r.status_code == 200:
        body = r.json()
        return {"ok": True, "chunks": body.get("chunks_indexed", 0),
                "articles": body.get("articles_found", 0),
                "proyecto_id": body.get("proyecto_id")}
    else:
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}


def main():
    logger.info("🧬 [AGENT] Iniciando ingesta RAG en GCP Cloud Run...")

    with httpx.Client(timeout=httpx.Timeout(connect=30.0, read=660.0, write=60.0, pool=10.0)) as client:
        token = get_token(client)
        seed_tipos_norma(client, token)

        ok, failed = 0, 0
        for doc in DOCUMENTOS:
            logger.info(f"🌐 [REQ] Ingesta GCP: {doc['file']} | {doc['jurisdiccion']}")
            result = ingest_pdf(client, token, doc)

            if result["ok"]:
                logger.info(
                    f"✅ [OK] {doc['file']} → "
                    f"{result['chunks']} chunks | "
                    f"{result['articles']} artículos | "
                    f"proyecto_id={result['proyecto_id']}"
                )
                ok += 1
            else:
                logger.error(f"❌ [FAULT] {doc['file']} → {result['error']}")
                failed += 1

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Ingesta GCP completada: {ok} exitosos | {failed} fallidos")


if __name__ == "__main__":
    main()
