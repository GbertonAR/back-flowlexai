"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: normative_hierarchy.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Jerarquía normativa argentina y control de versiones de la CN.
             Fundamento: Art. 31 CN (supremacía constitucional) y
             Art. 75 inc. 22 CN (bloque de constitucionalidad).
             Incluye detección de versiones históricas de la CN
             para evitar respuestas con artículos renumerados o derogados.
FECHA CREACIÓN: 2026-05-12
ÚLTIMA MODIFICACIÓN: 2026-05-12
REF. TICKET: #FS-011-RAG
"""

import re
from typing import Optional

# ── Jerarquía normativa argentina ─────────────────────────────────────────────
# Fundamento legal:
#   Art. 31 CN  → supremacía de la CN y leyes nacionales sobre derecho provincial
#   Art. 75 inc. 22 CN → tratados internacionales con jerarquía constitucional
#                        crean el "bloque de constitucionalidad"
#
# Nivel 1 = máxima jerarquía
HIERARCHY_MAP: dict = {
    # Bloque de constitucionalidad (Art. 31 + Art. 75 inc. 22 CN)
    "Constitucion Nacional": 1,
    "Constitucion":          1,
    "Tratado Internacional": 1,   # Solo los del Art. 75 inc. 22 (CADH, PIDCP, etc.)
    # Constituciones provinciales (supremacía local — Art. 31 CN)
    "Constitucion Provincial": 2,
    # Leyes orgánicas / complementarias de la CN
    "Ley Organica":    3,
    "Ley Especial":    3,
    # Leyes ordinarias y códigos
    "Ley":    4,
    "Codigo": 4,
    # Decretos-ley (fuerza de ley, sin proceso legislativo completo)
    "Decreto Ley": 5,
    # Decretos, reglamentos y ordenanzas
    "Decreto":    6,
    "Reglamento": 6,
    "Ordenanza":  6,    # Derecho municipal
    # Resoluciones y disposiciones
    "Resolucion":  7,
    "Disposicion": 7,
    "Circular":    7,
    "Instruccion": 7,
}

HIERARCHY_MAX = 7
# Peso del bonus jerárquico sobre la distancia L2 del reranker.
# Valor calibrado para que la CN tenga ~0.17 de reducción en distancia
# sin desplazar chunks irrelevantes de alta jerarquía.
HIERARCHY_WEIGHT = 0.20

# ── Control de versiones de la Constitución Nacional ─────────────────────────
# PROBLEMA ESPECÍFICO: El Art. 86 histórico (texto 1853-1957) ya no existe
# en el texto vigente de 1994. Los artículos fueron renumerados y el contenido
# modificado. Incluir versiones intermedias sin etiqueta de versión puede causar
# que el LLM cite artículos derogados o con numeración incorrecta.
#
# Ejemplo concreto:
#   Art. 86 (texto 1853/60): regulaba atribuciones del PEN
#   Art. 86 (texto 1994):    Defensor del Pueblo (institución nueva)
#
# Solución: marcar cada chunk CN con su versión de texto para que el
# reranker penalice versiones no vigentes en consultas generales.

CN_VIGENTE_VERSION = "1994"

CN_VERSIONS: dict = {
    "1994": "Texto vigente — Reforma constitucional 22-ago-1994 (Santa Fe/Paraná)",
    "1957": "Reforma parcial 1957 — Incorpora Art. 14 bis (derechos sociales)",
    "1898": "Reforma parcial 1898 — Modifica número de ministros y representantes",
    "1866": "Reforma parcial 1866 — Rentas de aduana y contribuciones",
    "1853": "Texto original 1853/60 — Constitución de la Confederación Argentina",
}

# Penalidad sobre distancia L2 para versiones CN no vigentes
CN_VERSION_PENALTY = 0.35

# Regex para detectar la versión del texto en los primeros 3000 caracteres
_CN_YEAR_RE = re.compile(
    r"\b(1994|1957|1898|1866|1853)\b",
    re.IGNORECASE,
)
_CN_DETECT_RE = re.compile(
    r"Constituci[oó]n\s+(?:de\s+la\s+Naci[oó]n\s+)?Argentina",
    re.IGNORECASE,
)


# ── API pública ───────────────────────────────────────────────────────────────

def get_hierarchy_level(tipo_norma: Optional[str]) -> int:
    """Retorna nivel jerárquico (1 = máximo). Desconocido → nivel mínimo."""
    if not tipo_norma:
        return HIERARCHY_MAX
    
    # Normalización robusta: quitar tildes y pasar a Título
    normalized = tipo_norma.strip().lower()
    normalized = normalized.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    normalized = normalized.title()
    
    return HIERARCHY_MAP.get(normalized, HIERARCHY_MAX)


def hierarchy_distance_bonus(hierarchy_level: int) -> float:
    """Reducción de distancia L2 por jerarquía normativa (CN → max bonificación)."""
    return HIERARCHY_WEIGHT * (HIERARCHY_MAX - hierarchy_level) / HIERARCHY_MAX


def detect_cn_version(text: str) -> Optional[str]:
    """
    Detecta la versión del texto de la CN escaneando los primeros 3000 caracteres.
    Retorna el año de la versión más reciente encontrada, o None si no es un doc CN.
    """
    header = text[:3000]
    if not _CN_DETECT_RE.search(header):
        return None
    years_found = [int(m.group(1)) for m in _CN_YEAR_RE.finditer(header)]
    if not years_found:
        return CN_VIGENTE_VERSION  # Default: asumir vigente
    # La versión del texto es la más reciente reforma mencionada en el encabezado
    candidate = str(max(y for y in years_found if y in (1853, 1866, 1898, 1957, 1994)))
    return candidate


def is_cn_document(tipo_norma: Optional[str]) -> bool:
    """Verdadero si el tipo de norma corresponde a la Constitución Nacional."""
    if not tipo_norma:
        return False
    t = tipo_norma.strip().lower()
    return "constitucion" in t and ("nacional" in t or t == "constitucion")
