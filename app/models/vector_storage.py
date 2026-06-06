## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: vector_storage.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Modelo de persistencia para fragmentos vectoriales (RAG).
             Vincula el contenido textual con el índice FAISS.
FECHA CREACIÓN: 2026-05-13
ÚLTIMA MODIFICACIÓN: 2026-05-13
REF. TICKET: #FS-FAISS-001
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, Dict
from datetime import datetime, timezone
import json

class DocumentChunk(SQLModel, table=True):
    """
    Representa un fragmento de texto indexado para búsqueda vectorial.
    Sustituye la persistencia interna de ChromaDB para mayor control y auditoría.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    proyecto_id: Optional[int] = Field(default=None, foreign_key="proyecto.id", index=True)
    
    # Contenido y Posicionamiento
    content: str = Field(description="Texto del fragmento")
    page_number: Optional[int] = Field(default=1)
    chunk_index: int = Field(default=0)
    
    # Trazabilidad
    source_name: str = Field(max_length=255, index=True)
    doc_hash: str = Field(max_length=64, index=True)
    
    # El vínculo con FAISS
    # El 'vector_id' es la posición (row index) en el índice FAISS del Tenant
    vector_id: int = Field(index=True, description="Índice en el archivo .index de FAISS")
    
    # Metadatos extendidos (Jurisdicción, Jerarquía, etc.)
    metadata_json: str = Field(default="{}", description="Metadatos en formato JSON")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def metadata_dict(self) -> Dict:
        try:
            return json.loads(self.metadata_json)
        except:
            return {}

    @metadata_dict.setter
    def metadata_dict(self, data: Dict):
        self.metadata_json = json.dumps(data)
