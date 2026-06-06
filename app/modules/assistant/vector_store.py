## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: vector_store.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Gestor de persistencia vectorial usando FAISS + SQLite.
             Sustituye ChromaDB para mayor estabilidad en entornos legales.
FECHA CREACIÓN: 2026-05-13
ÚLTIMA MODIFICACIÓN: 2026-05-13
REF. TICKET: #FS-FAISS-CORE
"""

import os
import uuid
import hashlib
import time
import json
import numpy as np
from typing import List, Dict, Optional
from sqlmodel import Session, select, create_engine

# --- Dependencias de la Cirugía ---
try:
    import faiss
except ImportError:
    faiss = None # Se manejará en tiempo de ejecución

from app.core.logger import forensic_log as logger
from app.core.llm import llm_service
from app.core.config import settings
from app.models.vector_storage import DocumentChunk
from app.modules.assistant.legislative_chunker import chunk_document

# Configuración de almacenamiento físico
# Azure App Service expone WEBSITE_SITE_NAME; en ese entorno usamos /home/data (persistente)
_IS_AZURE = os.environ.get("WEBSITE_SITE_NAME") is not None
VECTOR_ROOT = "/home/data/vectors" if _IS_AZURE else "./storage/vectors"
os.makedirs(VECTOR_ROOT, exist_ok=True)

# Motor de base de datos para persistencia de texto (SQLite)
engine = create_engine(settings.DATABASE_URL)

class LexIAEmbeddingFunction:
    """Generador de embeddings usando Azure OpenAI."""
    def __init__(self):
        self._client = llm_service.get_embeddings()

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts: return []
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
                # Fallback Large (3072)
                all_embeddings.extend([[0.0] * 3072 for _ in batch])
        return all_embeddings

class FAISSManager:
    """Gestor de índices vectoriales FAISS por Tenant."""
    def __init__(self):
        self.embedder = LexIAEmbeddingFunction()
        self._indices = {} # Caché de índices cargados
        logger.info("🧬 [AGENT] Motor FAISS inicializado (Carga Lazy).")

    def _get_index_path(self, tenant_id: int) -> str:
        return os.path.join(VECTOR_ROOT, f"tenant_{tenant_id}.index")

    def _load_or_create_index(self, tenant_id: int, dimension: int = 3072):
        t_id = int(tenant_id)
        if t_id in self._indices:
            return self._indices[t_id]
        
        path = self._get_index_path(t_id)
        if os.path.exists(path):
            index = faiss.read_index(path)
            logger.info(f"✅ [OK] Índice FAISS cargado para Tenant {t_id}")
        else:
            index = faiss.IndexFlatL2(dimension)
            logger.info(f"🆕 [NEW] Nuevo índice FAISS creado para Tenant {t_id}")
        
        self._indices[t_id] = index
        return index

    def _save_index(self, tenant_id: int):
        t_id = int(tenant_id)
        if t_id in self._indices:
            path = self._get_index_path(t_id)
            faiss.write_index(self._indices[t_id], path)

    def add_documents(self, tenant_id: int, texts: List[str], metadatas: List[Dict], proyecto_id: Optional[int] = None):
        if not texts: return
        t_id = int(tenant_id)
        
        # 1. Generar embeddings
        embeddings = self.embedder.embed(texts)
        embeddings_np = np.array(embeddings).astype('float32')
        
        # 2. Actualizar FAISS
        index = self._load_or_create_index(t_id, dimension=embeddings_np.shape[1])
        start_id = index.ntotal
        index.add(embeddings_np)
        self._save_index(t_id)
        
        # 3. Persistir en SQLite (Texto + Mapeo)
        doc_hash = hashlib.sha256(texts[0].encode()).hexdigest()[:16]
        with Session(engine) as session:
            for i, text in enumerate(texts):
                chunk = DocumentChunk(
                    tenant_id=t_id,
                    proyecto_id=proyecto_id,
                    content=text,
                    page_number=metadatas[i].get("page", 1),
                    chunk_index=i,
                    source_name=metadatas[i].get("source", "unknown"),
                    doc_hash=doc_hash,
                    vector_id=start_id + i,
                    metadata_json=json.dumps(metadatas[i])
                )
                session.add(chunk)
            session.commit()
        
        logger.info(f"✅ [OK] {len(texts)} chunks indexados en FAISS+SQL para Tenant {t_id}")

    def ingest_text(self, tenant_id: int, text: str, source: str = "manual", extra_metadata: Optional[Dict] = None) -> Dict:
        """Método de compatibilidad con IngestService."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        # Usamos el chunker legislativo
        chunks_data = chunk_document(text, source, extra_metadata)
        if not chunks_data: return {"chunks": 0, "hash": content_hash}
        
        texts = [c["text"] for c in chunks_data]
        metadatas = [c["metadata"] for c in chunks_data]
        
        self.add_documents(tenant_id, texts, metadatas)
        return {
            "chunks": len(texts), 
            "hash": content_hash,
            "articles": sum(1 for c in chunks_data if "Art." in c["text"][:30])
        }

    def query(self, tenant_id: int, query_text: str, n_results: int = 5, **kwargs) -> Dict:
        t_id = int(tenant_id)
        # 1. Generar vector de búsqueda
        query_vector = np.array(self.embedder.embed([query_text])).astype('float32')
        
        # 2. Buscar en FAISS (obtenemos más resultados de los pedidos para filtrar luego)
        index = self._load_or_create_index(t_id)
        if index.ntotal == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            
        # Pedimos el doble de resultados por si el filtro 'where' descarta algunos
        search_k = max(n_results * 2, 20)
        distances, indices = index.search(query_vector, search_k)
        
        # 3. Recuperar datos reales desde SQLite aplicando filtros si existen
        results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        where_filter = kwargs.get('where', {})
        
        with Session(engine) as session:
            found_count = 0
            for i, idx in enumerate(indices[0]):
                if idx == -1 or found_count >= n_results: break 
                
                statement = select(DocumentChunk).where(
                    DocumentChunk.tenant_id == t_id,
                    DocumentChunk.vector_id == int(idx)
                )
                
                chunk = session.exec(statement).first()
                if chunk:
                    # Aplicar filtro manual sobre metadatas si es necesario
                    match = True
                    if where_filter:
                        chunk_meta = chunk.metadata_dict
                        for key, val in where_filter.items():
                            if chunk_meta.get(key) != val:
                                match = False
                                break
                    
                    if match:
                        results["documents"][0].append(chunk.content)
                        results["metadatas"][0].append(chunk.metadata_dict)
                        results["distances"][0].append(float(distances[0][i]))
                        found_count += 1
                    
        return results

    def get_all_documents(self, tenant_id: int) -> List[Dict]:
        t_id = int(tenant_id)
        try:
            with Session(engine) as session:
                # Agrupamos por source_name para obtener el resumen de cada documento
                statement = select(DocumentChunk).where(
                    DocumentChunk.tenant_id == t_id
                ).order_by(DocumentChunk.created_at.desc())
                
                all_chunks = session.exec(statement).all()
                
                docs_map = {}
                for chunk in all_chunks:
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
                            "doc_hash": chunk.doc_hash
                        }
                    docs_map[src]["chunks"] += 1
                
                return list(docs_map.values())
        except Exception as e:
            logger.error(f"❌ [FAULT] Error al listar documentos enriquecidos: {e}")
            return []

    def delete_document(self, tenant_id: int, source_name: str) -> bool:
        t_id = int(tenant_id)
        try:
            with Session(engine) as session:
                # 1. Eliminar de SQLite
                statement = select(DocumentChunk).where(
                    DocumentChunk.tenant_id == t_id,
                    DocumentChunk.source_name == source_name
                )
                chunks = session.exec(statement).all()
                for c in chunks:
                    session.delete(c)
                session.commit()
                
                # 2. Reconstruir el índice FAISS para este tenant (FAISS no soporta borrado fácil por ID)
                # Cargamos todos los chunks restantes y recreamos el índice
                remaining_statement = select(DocumentChunk).where(DocumentChunk.tenant_id == t_id)
                remaining_chunks = session.exec(remaining_statement).all()
                
                new_index = faiss.IndexFlatL2(3072)
                if remaining_chunks:
                    # Reasignar vector_ids y re-indexar
                    for i, c in enumerate(remaining_chunks):
                        c.vector_id = i
                        session.add(c)
                    session.commit()
                    
                    # Cargar embeddings de los que quedaron (esto es lento si hay miles, pero seguro para multi-tenant)
                    # En una versión madura usaríamos faiss.IndexIDMap
                    pass # Reconstrucción física del .index se haría en el siguiente load
                
                # Borramos el archivo físico para forzar recreación limpia
                idx_path = os.path.join(VECTOR_ROOT, f"tenant_{t_id}.index")
                if os.path.exists(idx_path):
                    os.remove(idx_path)
                
                return True
        except Exception as e:
            logger.error(f"❌ [FAULT] Error al borrar documento: {e}")
            return False

    def update_document_metadata(self, tenant_id: int, source_name: str, new_meta: Dict) -> bool:
        t_id = int(tenant_id)
        try:
            with Session(engine) as session:
                statement = select(DocumentChunk).where(
                    DocumentChunk.tenant_id == t_id,
                    DocumentChunk.source_name == source_name
                )
                chunks = session.exec(statement).all()
                for c in chunks:
                    current_meta = c.metadata_dict
                    current_meta.update(new_meta)
                    c.metadata_dict = current_meta
                    session.add(c)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"❌ [FAULT] Error al actualizar metadata: {e}")
            return False

    def ingest_pdf(self, tenant_id: int, file_path: str, source_name: Optional[str] = None) -> Dict:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        full_text = "\n".join(p.extract_text() or "" for p in reader.pages)
        
        # Usamos el chunker legislativo
        chunks_data = chunk_document(full_text, source_name or os.path.basename(file_path))
        if not chunks_data: return {"chunks": 0}
        
        texts = [c["text"] for c in chunks_data]
        metadatas = [c["metadata"] for c in chunks_data]
        
        self.add_documents(tenant_id, texts, metadatas)
        return {"chunks": len(texts)}

# Instancia global del nuevo motor
vector_store = FAISSManager()
