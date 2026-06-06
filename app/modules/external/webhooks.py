## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: webhooks.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Sistema de despacho de eventos (Webhooks) para suscripciones externas.
FECHA CREACIÓN: 2026-03-25
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-023-INT
"""

import httpx
from typing import Dict, Any
from app.core.logger import forensic_log as logger

class WebhookDispatcher:
    """
    Envía notificaciones JSON a URLs externas registradas por los tenants.
    """

    async def dispatch_event(self, event_type: str, payload: Dict[str, Any], target_url: str):
        """🌐 [REQ] Despacha un evento a una URL externa."""
        logger.info(f"🌐 [REQ] Despachando evento {event_type} a {target_url}")
        
        event_data = {
            "event": event_type,
            "system": "LexIA Core",
            "data": payload
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(target_url, json=event_data, timeout=5.0)
                logger.info(f"✅ [OK] Webhook entregado: Status {response.status_code}")
                return response.status_code
            except Exception as e:
                logger.error(f"❌ [FAULT] Error entregando Webhook: {str(e)}")
                return None

webhook_dispatcher = WebhookDispatcher()
