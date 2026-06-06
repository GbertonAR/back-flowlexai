## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: test_subscriptions.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Test de integración para validar el sistema de suscripciones (Fase 3.2).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user

client = TestClient(app)

def test_create_subscription():
    # Usamos el dev-token-999 bypass implícito en deps.py si es necesario
    # o simplemente mockeamos el user
    payload = {
        "tenant_id": 999,
        "user_id": 999,
        "keywords": ["transporte", "seguridad vial"],
        "is_active": True,
        "notify_email": True
    }
    
    # Inyectamos el header de bypass que implementamos antes
    headers = {"Authorization": "Bearer dev-token-999"}
    
    response = client.post("/api/v1/subscriptions/", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["keywords"] == ["transporte", "seguridad vial"]

def test_list_subscriptions():
    headers = {"Authorization": "Bearer dev-token-999"}
    response = client.get("/api/v1/subscriptions/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
