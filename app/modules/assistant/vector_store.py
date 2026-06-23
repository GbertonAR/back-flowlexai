"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: vector_store.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Gestor de persistencia vectorial respaldado por la base de datos.
             Embeddings almacenados como JSON en DocumentChunk.embedding_json.
             Similitud coseno calculada en memoria via numpy (TTL-cache por tenant).
             Compatible con SQLite (dev) y PostgreSQL (prod/cloud). Sin archivos
             en disco — resuelve B2-FAISS para GCP Cloud Run.
FECHA CREACIÓN: 2026-05-13
ÚLTIMA MODIFICACIÓN: 2026-06-14
REF. TICKET: #FS-B2-PGVECTOR
"""

import json
import time
import hashlib
import numpy as np
from typing import List, Dict, Optional
from sqlmodel import Session, select, create_engine

from app.core.logger import forensic_log as logger
from app.core.llm import llm_service
from app.core.config import settings
from app.models.vector_storage import DocumentChunk
from app.modules.assistant.legislative_chunker import chunk_document

_is_sqlite = "sqlite" in settings.DATABASE_URL.lower()
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"timeout": 30, "check_same_thread": False} if _is_sqlite else {},
)

_CACHE_TTL = 300  # segundos — tiempo de vida del caché de embeddings por tenant


class LexIAEmbeddingFunction:
    """Generador de embeddings usando Azure OpenAI."""

    def __init__(self):
        self._client = llm_service.get_embeddings()

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        batch_size = 4
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                res = self._client.embed_documents(batch)
                all_embeddings.extend(res)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ [FAULT] Error en embeddings: {e}")
                all_embeddings.extend([[0.0] * 3072 for _ in batch])
        return all_embeddings


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class PGVectorManager:
    """
    Motor de búsqueda vectorial sin dependencias de disco.

    Embeddings viven en DocumentChunk.embedding_json (TEXT).
    Carga los vectores del tenant en memoria con caché TTL de 5 minutos.
    La similitud coseno se calcula con numpy — sin pgvector extension requerida.
    """

    def __init__(self):
        self.embedder = LexIAEmbeddingFunction()
        # { tenant_id: (timestamp_float, { chunk_id: (vector, content, metadata_dict) }) }
        self._cache: Dict[int, tuple] = {}
        logger.info("🧬 [AGENT] Motor PGVector (DB-backed, sin disco) inicializado.")

    # ──────────────────────────────────────────────────────────────────────────
    # Caché de vectores por tenant
    # ──────────────────────────────────────────────────────────────────────────

    def _load_tenant_vectors(self, tenant_id: int) -> Dict[int, tuple]:
        t_id = int(tenant_id)
        cached = self._cache.get(t_id)
        if cached:
            ts, data = cached
            if time.time() - ts < _CACHE_TTL:
                return data

        data: Dict[int, tuple] = {}
        try:
            with Session(engine) as session:
                chunks = session.exec(
                    select(DocumentChunk).where(DocumentChunk.tenant_id == t_id)
                ).all()
                for chunk in chunks:
                    if not chunk.embedding_json or chunk.embedding_json == "[]":
                        continue
                    vec = np.array(json.loads(chunk.embedding_json), dtype="float32")
                    data[chunk.id] = (vec, chunk.content, chunk.metadata_dict)
        except Exception as e:
            logger.warning(f"⚠️ [WORKFLOW] No se pudieron cargar vectores del Tenant {t_id}: {e}")
            return data

        self._cache[t_id] = (time.time(), data)
        return data

    def _invalidate_cache(self, tenant_id: int):
        self._cache.pop(int(tenant_id), None)

    # ──────────────────────────────────────────────────────────────────────────
    # Escritura
    # ──────────────────────────────────────────────────────────────────────────

    def add_documents(
        self,
        tenant_id: int,
        texts: List[str],
        metadatas: List[Dict],
        proyecto_id: Optional[int] = None,
    ):
        if not texts:
            return
        t_id = int(tenant_id)
        embeddings = self.embedder.embed(texts)
        doc_hash = hashlib.sha256(texts[0].encode()).hexdigest()[:16]

        with Session(engine) as session:
            for i, (text, meta, emb) in enumerate(zip(texts, metadatas, embeddings)):
                chunk = DocumentChunk(
                    tenant_id=t_id,
                    proyecto_id=proyecto_id,
                    content=text,
                    page_number=meta.get("page", 1),
                    chunk_index=i,
                    source_name=meta.get("source", "unknown"),
                    doc_hash=doc_hash,
                    embedding_json=json.dumps(emb),
                    metadata_json=json.dumps(meta),
                )
                session.add(chunk)
            session.commit()

        self._invalidate_cache(t_id)
        logger.info(f"✅ [OK] {len(texts)} chunks indexados en BD para Tenant {t_id}")

    def ingest_text(
        self,
        tenant_id: int,
        text: str,
        source: str = "manual",
        extra_metadata: Optional[Dict] = None,
    ) -> Dict:
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        chunks_data = chunk_document(text, source, extra_metadata)
        if not chunks_data:
            return {"chunks": 0, "hash": content_hash}

        texts = [c["text"] for c in chunks_data]
        metadatas = [c["metadata"] for c in chunks_data]
        self.add_documents(tenant_id, texts, metadatas)
        return {
            "chunks": len(texts),
            "hash": content_hash,
            "articles": sum(1 for c in chunks_data if "Art." in c["text"][:30]),
        }

    def ingest_pdf(
        self, tenant_id: int, file_path: str, source_name: Optional[str] = None
    ) -> Dict:
        import os
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        full_text = "\n".join(p.extract_text() or "" for p in reader.pages)
        chunks_data = chunk_document(full_text, source_name or os.path.basename(file_path))
        if not chunks_data:
            return {"chunks": 0}
        texts = [c["text"] for c in chunks_data]
        metadatas = [c["metadata"] for c in chunks_data]
        self.add_documents(tenant_id, texts, metadatas)
        return {"chunks": len(texts)}

    # ──────────────────────────────────────────────────────────────────────────
    # Consulta
    # ──────────────────────────────────────────────────────────────────────────

    def query(
        self, tenant_id: int, query_text: str, n_results: int = 5, **kwargs
    ) -> Dict:
        t_id = int(tenant_id)
        query_vec = np.array(self.embedder.embed([query_text])[0], dtype="float32")
        tenant_data = self._load_tenant_vectors(t_id)

        if not tenant_data:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        where_filter = self._parse_where_filter(kwargs.get("where", {}))

        scored = []
        for _id, (vec, content, meta) in tenant_data.items():
            if where_filter and any(meta.get(k) != v for k, v in where_filter.items()):
                continue
            sim = _cosine_similarity(query_vec, vec)
            scored.append((sim, content, meta))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n_results]

        return {
            "documents": [[item[1] for item in top]],
            "metadatas": [[item[2] for item in top]],
            # distancia coseno = 1 − similitud (compatible con la interfaz anterior)
            "distances": [[1.0 - item[0] for item in top]],
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Gestión de documentos
    # ──────────────────────────────────────────────────────────────────────────

    def get_all_documents(self, tenant_id: int) -> List[Dict]:
        t_id = int(tenant_id)
        try:
            with Session(engine) as session:
                chunks = session.exec(
                    select(DocumentChunk)
                    .where(DocumentChunk.tenant_id == t_id)
                    .order_by(DocumentChunk.created_at.desc())
                ).all()
                docs_map: Dict[str, Dict] = {}
                for chunk in chunks:
                    src = chunk.source_name
                    if src not in docs_map:
                        meta = chunk.metadata_dict
                        docs_map[src] = {
                            "name": src,
                            "chunks": 0,
                            "jurisdiccion": meta.get("jurisdiccion", "Nacional"),
                            "jerarquia": meta.get("tipo_norma", "Ley"),
                            "hierarchy_level": meta.get("hierarchy_level", 3),
                            "created_at": chunk.created_at.isoformat(),
                            "doc_hash": chunk.doc_hash,
                        }
                    docs_map[src]["chunks"] += 1
                return list(docs_map.values())
        except Exception as e:
            logger.error(f"❌ [FAULT] Error al listar documentos: {e}")
            return []

    def delete_document(self, tenant_id: int, source_name: str) -> bool:
        t_id = int(tenant_id)
        try:
            with Session(engine) as session:
                chunks = session.exec(
                    select(DocumentChunk).where(
                        DocumentChunk.tenant_id == t_id,
                        DocumentChunk.source_name == source_name,
                    )
                ).all()
                for c in chunks:
                    session.delete(c)
                session.commit()
            self._invalidate_cache(t_id)
            return True
        except Exception as e:
            logger.error(f"❌ [FAULT] Error al borrar documento: {e}")
            return False

    def update_document_metadata(
        self, tenant_id: int, source_name: str, new_meta: Dict
    ) -> bool:
        t_id = int(tenant_id)
        try:
            with Session(engine) as session:
                chunks = session.exec(
                    select(DocumentChunk).where(
                        DocumentChunk.tenant_id == t_id,
                        DocumentChunk.source_name == source_name,
                    )
                ).all()
                for c in chunks:
                    current = c.metadata_dict
                    current.update(new_meta)
                    c.metadata_json = json.dumps(current)
                    session.add(c)
                session.commit()
            self._invalidate_cache(t_id)
            return True
        except Exception as e:
            logger.error(f"❌ [FAULT] Error al actualizar metadata: {e}")
            return False

    def get_document_count(self, tenant_id) -> int:
        t_id = int(tenant_id)
        try:
            with Session(engine) as session:
                chunks = session.exec(
                    select(DocumentChunk).where(DocumentChunk.tenant_id == t_id)
                ).all()
                return len({c.source_name for c in chunks})
        except Exception as e:
            logger.error(f"❌ [FAULT] Error al contar documentos: {e}")
            return 0

    # ──────────────────────────────────────────────────────────────────────────
    # Utilidades internas
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_where_filter(self, where_filter: dict) -> dict:
        if not where_filter:
            return {}
        simple: dict = {}
        if "$and" in where_filter:
            for cond in where_filter["$and"]:
                simple.update(self._parse_where_filter(cond))
            return simple
        if "$or" in where_filter:
            for cond in where_filter["$or"]:
                simple.update(self._parse_where_filter(cond))
            return simple
        for key, val in where_filter.items():
            simple[key] = val["$eq"] if isinstance(val, dict) and "$eq" in val else val
        return simple


# Instancia global — reemplaza FAISSManager
vector_store = PGVectorManager()
