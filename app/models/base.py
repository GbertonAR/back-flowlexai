## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: base.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Consolidador de Modelos para el autogenerador de Alembic.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-07
REF. TICKET: #FS-003
"""

# Este archivo importa todos los modelos SQLModel para que Alembic los detecte
from app.models.tenant import Tenant  # noqa: F401
from app.models.auditoria import AuditoriaLog  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.ip_registry.data_source import DataSource  # noqa: F401
from app.models.ip_registry.data_lineage import DataLineage  # noqa: F401
from app.models.hitl.hitl_review import HITLReview  # noqa: F401
from app.models.bias_report import BiasReport  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.legislative import Bloque, Comision, Legislador  # noqa: F401
from app.models.expediente import Proyecto, TipoNorma, Dictamen  # noqa: F401

__all__ = [
    "Tenant", "AuditoriaLog", "User", "DataSource", "DataLineage", 
    "HITLReview", "BiasReport", "Subscription",
    "Bloque", "Comision", "Legislador", "Proyecto", "TipoNorma", "Dictamen"
]
