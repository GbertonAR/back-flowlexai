## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: logger.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Implementación del Patrón de Logging Forense (Observabilidad). WFD Compliant.
FECHA CREACIÓN: 2026-03-07
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-005
"""

import logging
import sys
from pathlib import Path

# Asegurar que el directorio de logs exista
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Cumplimiento Regla 6 (ACTUALIZADA): Nombre genérico debug_[nombre_Proyecto].log
LOG_FILE = LOG_DIR / "debug_FlowLexAI.log"

# Iconos requeridos por la Regla 6
LOG_ICONS = {
    "REQ": "🌐 [REQ]",
    "WORKFLOW": "🧠 [WORKFLOW]",
    "AGENT": "🧬 [AGENT]",
    "OK": "✅ [OK]",
    "FAULT": "❌ [FAULT]"
}

class ForensicFormatter(logging.Formatter):
    """
    Formateador personalizado para la Inmutabilidad Forense:
    Formato: 2026-03-07 15:45:32 - [RequestID] - ICONO: Mensaje
    """
    def format(self, record):
        request_id = getattr(record, "request_id", "--------")
        return f"{self.formatTime(record, self.datefmt)} | REQ:{request_id} | {record.levelname} | {record.msg}"

def setup_forensic_logger(name: str = "FlowLex") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    
    if not logger.handlers:
        formatter = ForensicFormatter()
        
        utf8_stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, closefd=False)
        console_handler = logging.StreamHandler(utf8_stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # Alertas por email ante errores (rate-limit 5 min, hilo daemon)
        from app.core.email_alerts import error_email_handler
        error_email_handler.setFormatter(formatter)
        logger.addHandler(error_email_handler)

    return logger

forensic_log = setup_forensic_logger()
