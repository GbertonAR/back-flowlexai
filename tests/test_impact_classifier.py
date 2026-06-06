"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: test_impact_classifier.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Tests unitarios para ImpactClassifier. Valida la lógica de
             clasificación HITL y el fallback heurístico (WFD Dir 2.1).
FECHA CREACIÓN: 2026-05-12
ÚLTIMA MODIFICACIÓN: 2026-05-12
REF. TICKET: QW-01
"""

import pytest
from unittest.mock import MagicMock, patch
from app.modules.hitl.impact_classifier import ImpactClassifier


def _make_llm_mock(response_text: str) -> MagicMock:
    """Construye un mock de LLM que retorna response_text como contenido."""
    ai_msg = MagicMock()
    ai_msg.content = response_text
    llm_mock = MagicMock()
    llm_mock.invoke.return_value = ai_msg
    return llm_mock


class TestRequiresHITL:

    def test_critical_requires_hitl(self):
        assert ImpactClassifier.requires_hitl("CRITICAL") is True

    def test_high_requires_hitl(self):
        assert ImpactClassifier.requires_hitl("HIGH") is True

    def test_medium_no_hitl(self):
        assert ImpactClassifier.requires_hitl("MEDIUM") is False

    def test_low_no_hitl(self):
        assert ImpactClassifier.requires_hitl("LOW") is False

    def test_empty_string_no_hitl(self):
        assert ImpactClassifier.requires_hitl("") is False


class TestClassifyWithLLM:

    @patch("app.core.llm.llm_service")
    def test_llm_returns_low(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("LOW")
        result = ImpactClassifier.classify({"query": "¿Qué es una ley?", "response": "Una norma."})
        assert result == "LOW"

    @patch("app.core.llm.llm_service")
    def test_llm_returns_medium(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("MEDIUM")
        result = ImpactClassifier.classify({"query": "Regulación local", "response": "Aplica ordenanza."})
        assert result == "MEDIUM"

    @patch("app.core.llm.llm_service")
    def test_llm_returns_high(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("HIGH")
        result = ImpactClassifier.classify({"query": "Reforma del Código Penal", "response": "..."})
        assert result == "HIGH"

    @patch("app.core.llm.llm_service")
    def test_llm_returns_critical(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("CRITICAL")
        result = ImpactClassifier.classify({"query": "Constitucionalidad del decreto", "response": "..."})
        assert result == "CRITICAL"

    @patch("app.core.llm.llm_service")
    def test_llm_response_is_case_insensitive(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("high")
        result = ImpactClassifier.classify({"query": "algo", "response": "algo"})
        assert result == "HIGH"

    @patch("app.core.llm.llm_service")
    def test_llm_invalid_response_falls_back_to_low(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("EXTREME_RISK")
        result = ImpactClassifier.classify({"query": "algo", "response": "algo"})
        assert result == "LOW"

    @patch("app.core.llm.llm_service")
    def test_llm_response_with_whitespace_trimmed(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("  CRITICAL  ")
        result = ImpactClassifier.classify({"query": "constitucionalidad", "response": "..."})
        assert result == "CRITICAL"


class TestClassifyHeuristicFallback:

    @patch("app.core.llm.llm_service")
    def test_llm_exception_triggers_heuristic(self, mock_svc):
        mock_svc.get_chat_model.side_effect = Exception("Azure timeout")
        result = ImpactClassifier.classify({"query": "consulta simple", "response": "info."})
        assert result == "LOW"

    @patch("app.core.llm.llm_service")
    def test_heuristic_detects_critical_keyword_aprobacion(self, mock_svc):
        mock_svc.get_chat_model.side_effect = Exception("LLM down")
        result = ImpactClassifier.classify({"query": "aprobación del proyecto", "response": ""})
        assert result == "CRITICAL"

    @patch("app.core.llm.llm_service")
    def test_heuristic_detects_critical_keyword_voto(self, mock_svc):
        mock_svc.get_chat_model.side_effect = Exception("LLM down")
        result = ImpactClassifier.classify({"query": "resultado del voto en cámara", "response": ""})
        assert result == "CRITICAL"

    @patch("app.core.llm.llm_service")
    def test_heuristic_detects_critical_keyword_constitucionalidad(self, mock_svc):
        mock_svc.get_chat_model.side_effect = Exception("LLM down")
        result = ImpactClassifier.classify({"query": "análisis de constitucionalidad", "response": ""})
        assert result == "CRITICAL"

    @patch("app.core.llm.llm_service")
    def test_heuristic_in_response_also_detected(self, mock_svc):
        mock_svc.get_chat_model.side_effect = Exception("LLM down")
        result = ImpactClassifier.classify({"query": "consulta", "response": "implica sanción legal"})
        assert result == "CRITICAL"

    @patch("app.core.llm.llm_service")
    def test_heuristic_no_keywords_returns_low(self, mock_svc):
        mock_svc.get_chat_model.side_effect = Exception("LLM down")
        result = ImpactClassifier.classify({"query": "¿Qué es el quórum?", "response": "Mayoría requerida."})
        assert result == "LOW"

    @patch("app.core.llm.llm_service")
    def test_empty_payload_returns_low(self, mock_svc):
        mock_svc.get_chat_model.side_effect = Exception("LLM down")
        result = ImpactClassifier.classify({})
        assert result == "LOW"


class TestClassifyAndHITLIntegration:

    @patch("app.core.llm.llm_service")
    def test_critical_classify_triggers_hitl(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("CRITICAL")
        impact = ImpactClassifier.classify({"query": "q", "response": "r"})
        assert ImpactClassifier.requires_hitl(impact) is True

    @patch("app.core.llm.llm_service")
    def test_low_classify_no_hitl(self, mock_svc):
        mock_svc.get_chat_model.return_value = _make_llm_mock("LOW")
        impact = ImpactClassifier.classify({"query": "q", "response": "r"})
        assert ImpactClassifier.requires_hitl(impact) is False
