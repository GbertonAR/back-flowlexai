"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: legislative_chunker.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Chunker estructural para legislación argentina.
             Segmenta documentos por artículo respetando la jerarquía
             Libro → Título → Capítulo → Sección → Artículo.
             Soporta AKN XML (ISO 36000) y texto plano (PDF extraído).
             Cubre convenciones de legislación nacional, provincial y municipal.
FECHA CREACIÓN: 2026-05-12
ÚLTIMA MODIFICACIÓN: 2026-05-12
REF. TICKET: #FS-011-RAG
"""

import unicodedata
import re
from typing import List, Dict, Optional
from app.core.logger import forensic_log as logger

_MAX_ARTICLE_CHARS = 1800
_OVERLAP_CHARS = 150

# ── Detección de formato ──────────────────────────────────────────────────────
_AKN_DETECT_RE = re.compile(r"<akomaNtoso|legaldocml\.ns", re.IGNORECASE)

# ── Artículos ─────────────────────────────────────────────────────────────────
# Cubre convenciones nacionales, provinciales y municipales argentinas:
#   ARTÍCULO 1°.-  |  Artículo 1º.-  |  ART. 14 -  |  ARTICULO PRIMERO.-
_ART_NUM_PART = (
    r"(?:"
    r"\d+[°º]?"                                                         # arábigo
    r"|[IVXLCDM]{1,8}"                                                  # romano
    r"|PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO"
    r"|S[EÉ]PTIMO|OCTAVO|NOVENO"
    r"|D[EÉ]CIMO(?:\s+(?:PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO"
    r"|SEXTO|S[EÉ]PTIMO|OCTAVO|NOVENO))?"
    r"|VIGES(?:IMO)?(?:\s+\w+)?"
    r"|TRIG[EÉ]SIMO(?:\s+\w+)?"
    r"|CU[AÁ]DRAG[EÉ]SIMO(?:\s+\w+)?"
    r")"
)

_ARTICLE_RE = re.compile(
    rf"(?m)^[ \t]*(?:ART[IÍ]CULO|ART\.)\s+(?P<num>{_ART_NUM_PART})[°º]?\s*"
    r"(?:[-\.—:\s]{0,4})",
    re.IGNORECASE,
)

# ── Jerarquía de secciones ────────────────────────────────────────────────────
_SECTION_RE = re.compile(
    r"(?m)^[ \t]*(?P<stype>LIBRO|PARTE|T[IÍ]TULO|CAP[IÍ]TULO|SECCI[OÓ]N|ANEXO)\s+"
    r"(?P<snum>[IVXLCDM]{1,8}|\d+[°º]?)"
    r"(?:[ \t]*[-—.][ \t]*(?P<sheading>[^\n]{1,120}))?",
    re.IGNORECASE,
)

# Nivel de cada tipo de sección (menor número = mayor jerarquía)
_SECTION_LEVELS: Dict[str, int] = {
    "LIBRO": 0, "PARTE": 0,
    "TITULO": 1, "TÍTULO": 1,
    "CAPITULO": 2, "CAPÍTULO": 2,
    "SECCION": 3, "SECCIÓN": 3,
    "ANEXO": 10,
}

_ORDINAL_MAP: Dict[str, str] = {
    "PRIMERO": "1", "SEGUNDO": "2", "TERCERO": "3", "CUARTO": "4",
    "QUINTO": "5", "SEXTO": "6", "SÉPTIMO": "7", "SEPTIMO": "7",
    "OCTAVO": "8", "NOVENO": "9", "DÉCIMO": "10", "DECIMO": "10",
}

# Incisos para split de artículos largos: a), b), 1), i), ii)
_INCISO_RE = re.compile(r"\n(?=[a-záéíóú]\)|\d+\)|[ivx]+\))", re.IGNORECASE)


# ── API pública ───────────────────────────────────────────────────────────────

def chunk_document(
    text: str,
    source: str,
    extra_metadata: Optional[Dict] = None,
) -> List[Dict]:
    """
    Segmenta un documento legislativo en chunks estructurados por artículo.
    Detecta automáticamente AKN XML vs texto plano.

    Retorna lista de dicts {"text": str, "metadata": dict} listos para ChromaDB.
    """
    meta = extra_metadata or {}
    
    # ── Pre-proceso inteligente ──
    text = _normalize_and_clean(text)
    
    if _AKN_DETECT_RE.search(text[:1000]):
        logger.info(f"🧠 [WORKFLOW] Detectado formato Akoma Ntoso (XML) para '{source}'.")
        return _chunk_akn(text, source, meta)
    
    logger.info(f"🧠 [WORKFLOW] Detectado formato Texto Plano (PDF/TXT) para '{source}'.")
    return _chunk_plaintext(text, source, meta)


def _normalize_and_clean(text: str) -> str:
    """Aplica el pipeline de limpieza profunda (Unicode, control chars, guiones, headers)."""
    if not text:
        return ""
    
    # 1. Normalización Unicode (NFKC)
    text = unicodedata.normalize("NFKC", text)
    
    # 2. Eliminar caracteres de control no imprimibles (excepto \n y \t)
    # Esto limpia "basura" invisible que a veces arrastra el PDF
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\t")
    
    # 3. Recomponer palabras cortadas por guiones al final de línea
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    
    # 4. Limpieza de líneas de basura y unificación de espacios
    lines = text.splitlines()
    cleaned_lines = []
    garbage_count = 0
    
    garbage_patterns = [
        re.compile(r"^\s*P[aá]gina\s+\d+\s+de\s+\d+\s*$", re.I),
        re.compile(r"^\s*\d+\s*$", re.I),
        re.compile(r"^\s*CONSTITUCI[OÓ]N\s+DE\s+LA\s+CIUDAD.*$", re.I),
        re.compile(r"^\s*GOBIERNO\s+DE\s+LA\s+CIUDAD.*$", re.I),
        re.compile(r"^[-_\*\.\s]{5,}$"), # Líneas de separación (---, ***, etc)
    ]
    
    for line in lines:
        # Limpieza de espacios extras dentro de la línea
        line = " ".join(line.split())
        
        if not line:
            continue
            
        if any(p.match(line) for p in garbage_patterns):
            garbage_count += 1
            continue
            
        cleaned_lines.append(line)
    
    if garbage_count > 0:
        logger.info(f"🧠 [WORKFLOW] Limpieza Smart: {garbage_count} líneas de ruido eliminadas.")
        
    return "\n".join(cleaned_lines)


# ── Chunker texto plano ───────────────────────────────────────────────────────

def _chunk_plaintext(text: str, source: str, extra_meta: Dict) -> List[Dict]:
    chunks: List[Dict] = []
    section_path: Dict[int, str] = {}  # level → label

    current_num: str = ""
    current_heading: str = ""
    current_lines: List[str] = []
    preamble_lines: List[str] = []
    in_article: bool = False

    def flush() -> None:
        body = "\n".join(current_lines).strip()
        if not body:
            return
        _append_article_chunks(
            chunks, body, current_num, current_heading,
            _get_section_str(section_path), source, extra_meta,
        )

    for line in text.splitlines():
        # Encabezado de sección: actualiza jerarquía
        sec_m = _SECTION_RE.match(line)
        if sec_m:
            flush()
            in_article = False
            current_lines = []
            stype = sec_m.group("stype").upper()
            snum = sec_m.group("snum")
            sheading = (sec_m.group("sheading") or "").strip()
            label = f"{stype} {snum}" + (f" — {sheading}" if sheading else "")
            _update_section_path(section_path, stype, label)
            continue

        # Inicio de artículo
        art_m = _ARTICLE_RE.match(line)
        if art_m:
            flush()
            in_article = True
            current_lines = []
            current_num = _normalize_num(art_m.group("num"))
            rest = line[art_m.end():].strip()
            # Resto corto sin minúscula inicial → título del artículo
            if rest and len(rest) < 100 and not _looks_like_body(rest):
                current_heading = rest
            else:
                current_heading = ""
                if rest:
                    current_lines.append(rest)
            continue

        if in_article:
            current_lines.append(line)
        else:
            preamble_lines.append(line)

    flush()

    article_count = sum(1 for c in chunks if c["metadata"].get("chunk_type") == "article")
    section_count = len(set(c["metadata"].get("section") for c in chunks if c["metadata"].get("section")))
    
    if article_count == 0:
        logger.warning(f"⚠️ [WORKFLOW] No se detectaron artículos en '{source}'. ¿El formato es correcto?")
    else:
        logger.info(f"✅ [OK] Segmentación finalizada: {article_count} artículos y {section_count} secciones encontradas.")

    # Preámbulo (Visto y Considerandos) como chunk especial
    preamble = "\n".join(preamble_lines).strip()
    if len(preamble) > 150:
        chunks.insert(
            0,
            _make_chunk(
                text=preamble[:_MAX_ARTICLE_CHARS],
                chunk_type="preamble",
                article_num="",
                article_heading="Preámbulo / Visto y Considerandos",
                section="",
                source=source,
                split_index=0,
                is_split=False,
                extra_meta=extra_meta,
            ),
        )

    return chunks


def _looks_like_body(text: str) -> bool:
    return len(text) > 80 or text.endswith(".") or (bool(text) and text[0].islower())


# ── Chunker AKN XML ───────────────────────────────────────────────────────────

def _chunk_akn(xml_text: str, source: str, extra_meta: Dict) -> List[Dict]:
    from app.modules.akn.akn_parser import AkomaNtosoParser

    akn_meta = AkomaNtosoParser.parse_metadata(xml_text)
    articles = AkomaNtosoParser.extract_articles(xml_text)

    if not articles:
        body = AkomaNtosoParser.extract_body_text(xml_text)
        return _chunk_plaintext(body, source, extra_meta) if body else []

    enriched_meta = {
        **extra_meta,
        "akn_uri": akn_meta.get("uri", ""),
        "akn_date": akn_meta.get("date", ""),
    }

    chunks: List[Dict] = []
    for article in articles:
        parts = [article["content"]]
        for inc in article.get("sub_elements", []):
            parts.append(f"{inc['num']} {inc['text']}")
        body = "\n".join(parts).strip()
        if not body:
            continue
        _append_article_chunks(
            chunks,
            body,
            _normalize_num(article.get("num", "")),
            article.get("heading", ""),
            "",
            source,
            enriched_meta,
        )

    return chunks


# ── Utilidades internas ───────────────────────────────────────────────────────

def _append_article_chunks(
    chunks: List[Dict],
    body: str,
    num: str,
    heading: str,
    section: str,
    source: str,
    extra_meta: Dict,
) -> None:
    sub_texts = _split_long_article(body)
    is_split = len(sub_texts) > 1
    for i, sub in enumerate(sub_texts):
        label_parts: List[str] = []
        if section:
            label_parts.append(section)
        if num:
            label_parts.append(f"Art. {num}")
        if heading:
            label_parts.append(heading)
        prefix = "[" + " | ".join(label_parts) + "]" if label_parts else ""
        full_text = f"{prefix}\n{sub}".strip() if prefix else sub

        chunks.append(
            _make_chunk(
                text=full_text,
                chunk_type="article",
                article_num=num,
                article_heading=heading,
                section=section,
                source=source,
                split_index=i,
                is_split=is_split,
                extra_meta=extra_meta,
            )
        )


def _make_chunk(
    text: str,
    chunk_type: str,
    article_num: str,
    article_heading: str,
    section: str,
    source: str,
    split_index: int,
    is_split: bool,
    extra_meta: Dict,
) -> Dict:
    return {
        "text": text,
        "metadata": {
            "source": source,
            "chunk_type": chunk_type,
            "article_num": article_num,
            "article_heading": article_heading,
            "section": section,
            "split_index": split_index,
            "is_split": is_split,
            **extra_meta,
        },
    }


def _split_long_article(text: str) -> List[str]:
    """Divide artículos largos respetando límites de incisos primero."""
    if len(text) <= _MAX_ARTICLE_CHARS:
        return [text]

    # Intentar split por incisos (a), b), 1), i), ii))
    parts = _INCISO_RE.split(text)
    if len(parts) > 1:
        result: List[str] = []
        current = parts[0]
        for part in parts[1:]:
            candidate = current + "\n" + part
            if len(candidate) <= _MAX_ARTICLE_CHARS:
                current = candidate
            else:
                if current.strip():
                    result.append(current.strip())
                current = part
        if current.strip():
            result.append(current.strip())
        return result or [text[:_MAX_ARTICLE_CHARS]]

    # Fallback: corte por caracteres con overlap
    result = []
    start = 0
    while start < len(text):
        end = min(start + _MAX_ARTICLE_CHARS, len(text))
        result.append(text[start:end])
        start += _MAX_ARTICLE_CHARS - _OVERLAP_CHARS
    return result


def _normalize_num(raw: str) -> str:
    clean = raw.strip().rstrip("°º").strip()
    return _ORDINAL_MAP.get(clean.upper(), clean)


def _update_section_path(path: Dict[int, str], stype: str, label: str) -> None:
    """Actualiza la jerarquía eliminando niveles iguales o inferiores al actual."""
    stype_norm = stype.upper().replace("Í", "I").replace("Ó", "O").replace("É", "E")
    level = _SECTION_LEVELS.get(stype_norm, 10)
    for k in list(path.keys()):
        if k >= level:
            del path[k]
    path[level] = label


def _get_section_str(path: Dict[int, str]) -> str:
    return " > ".join(path[k] for k in sorted(path.keys()))
