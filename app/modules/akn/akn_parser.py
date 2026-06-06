## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: akn_parser.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Parser avanzado para el estándar Akoma Ntoso (ISO 36000). 
             Soporta extracción granular de artículos e identificación FRBR.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-005-GAP5
"""

import xml.etree.ElementTree as ET
import uuid
from typing import Dict, Optional, List
from app.core.logger import forensic_log as logger

class AkomaNtosoParser:
    """
    Parser avanzado para documentos legislativos en formato Akoma Ntoso (ISO 36000).
    Soporta extracción granular de artículos e identificación FRBR.
    """
    
    NS = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}

    @staticmethod
    def parse_metadata(xml_content: str) -> Dict:
        """Extrae metadatos de identificación del documento (FRBR completo)."""
        try:
            root = ET.fromstring(xml_content)
            frbr_id = root.find(".//akn:FRBRthis", AkomaNtosoParser.NS)
            frbr_uri = root.find(".//akn:FRBRuri", AkomaNtosoParser.NS)
            doc_date = root.find(".//akn:FRBRdate", AkomaNtosoParser.NS)
            frbr_author = root.find(".//akn:FRBRauthor", AkomaNtosoParser.NS)
            
            metadata = {
                "frbr_id": frbr_id.get("value") if frbr_id is not None else "unknown",
                "uri": frbr_uri.get("value") if frbr_uri is not None else "unknown",
                "date": doc_date.get("date") if doc_date is not None else "unknown",
                "author": frbr_author.get("href") if frbr_author is not None else "unknown",
                "type": root.tag.split('}')[-1] if '}' in root.tag else root.tag,
                "compliance": "WFD-Dir-AKN-3.0"
            }
            logger.info(f"✅ [OK] Metadatos AKN Soberanos extraídos: {metadata['frbr_id']}")
            return metadata
        except Exception as e:
            logger.error(f"❌ [FAULT] Error parsing AKN XML Metadata: {e}")
            return {"error": str(e)}

    @staticmethod
    def extract_articles(xml_content: str) -> List[Dict]:
        """Extrae artículos estructurados con incisos (points/slists)."""
        articles = []
        try:
            root = ET.fromstring(xml_content)
            blocks = root.findall(".//akn:article", AkomaNtosoParser.NS)
            
            for block in blocks:
                num = block.find("akn:num", AkomaNtosoParser.NS)
                heading = block.find("akn:heading", AkomaNtosoParser.NS)
                
                # Extraer párrafos directos
                paragraphs = block.findall("./akn:content/akn:p", AkomaNtosoParser.NS)
                if not paragraphs: # Fallback a búsqueda profunda
                    paragraphs = block.findall(".//akn:p", AkomaNtosoParser.NS)
                
                content_text = "\n".join(["".join(p.itertext()).strip() for p in paragraphs])
                
                # Extraer incisos (pueden ser 'point', 'list', etc.)
                points = block.findall(".//akn:point", AkomaNtosoParser.NS)
                incisos = []
                for p in points:
                    p_num = p.find("akn:num", AkomaNtosoParser.NS)
                    p_content = p.find("akn:content/akn:p", AkomaNtosoParser.NS)
                    incisos.append({
                        "num": "".join(p_num.itertext()).strip() if p_num is not None else "",
                        "text": "".join(p_content.itertext()).strip() if p_content is not None else ""
                    })
                
                articles.append({
                    "id": block.get("eId", str(uuid.uuid4())),
                    "num": "".join(num.itertext()).strip() if num is not None else "",
                    "heading": "".join(heading.itertext()).strip() if heading is not None else "",
                    "content": content_text,
                    "sub_elements": incisos
                })
            
            logger.info(f"✅ [OK] {len(articles)} artículos extraídos con {sum(len(a['sub_elements']) for a in articles)} incisos.")
            return articles
        except Exception as e:
            logger.error(f"❌ [FAULT] Error extrayendo artículos AKN: {e}")
            return []

    @staticmethod
    def extract_body_text(xml_content: str) -> str:
        """Extrae el texto plano completo para fallback."""
        articles = AkomaNtosoParser.extract_articles(xml_content)
        if articles:
            return "\n\n".join([f"{a['num']} {a['heading']}\n{a['content']}" for a in articles])
        return ""

akn_parser = AkomaNtosoParser()
