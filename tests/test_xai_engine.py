"""
SISTEMA: FlowState AI - Inteligencia Conectada
MÓDULO: test_xai_engine.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Tests unitarios para XAIEngine. Valida la generación de tarjetas
             de explicabilidad (WFD Dir 5.2) sin dependencias externas.
FECHA CREACIÓN: 2026-05-12
ÚLTIMA MODIFICACIÓN: 2026-05-12
REF. TICKET: QW-01
"""

import pytest
from app.modules.xai.xai_engine import XAIEngine
from app.modules.xai.explanation_card import ExplanationCard, XAISourceWeight


SOURCES_HIGH = [{"name": "Constitución Nacional", "relevance": 0.95}]
SOURCES_LOW  = [{"name": "Decreto 123/2024",      "relevance": 0.50}]
SOURCES_MIX  = [
    {"name": "Ley 26.944",  "relevance": 0.85},
    {"name": "Decreto 456", "relevance": 0.40},
]


class TestXAIEngineOutputStructure:

    def test_returns_explanation_card(self):
        result = XAIEngine.generate_explanation("Respuesta de prueba.", SOURCES_HIGH)
        assert isinstance(result, ExplanationCard)

    def test_card_has_all_required_fields(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH)
        assert result.confidence_score is not None
        assert isinstance(result.reasoning_steps, list)
        assert isinstance(result.sources, list)
        assert isinstance(result.limitations, list)
        assert result.wfd_compliance_ref == "Dir-5.2-Explainability"
        assert result.ai_model_version == "LexIA-Core-v1.0-GPT4o"
        assert result.generation_timestamp is not None

    def test_generation_timestamp_is_iso_format(self):
        from datetime import datetime
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH)
        # No debe lanzar excepción si es ISO válido
        dt = datetime.fromisoformat(result.generation_timestamp)
        assert dt is not None

    def test_limitations_are_always_present(self):
        result = XAIEngine.generate_explanation("Texto.", [])
        assert len(result.limitations) >= 1

    def test_default_confidence_score(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH)
        assert result.confidence_score == 0.95

    def test_custom_confidence_score(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH, confidence_score=0.75)
        assert result.confidence_score == 0.75


class TestXAIEngineSourceWeights:

    def test_high_relevance_maps_to_HIGH_impact(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH)
        assert result.sources[0].impact_level == "HIGH"
        assert result.sources[0].weight == 0.95

    def test_low_relevance_maps_to_MEDIUM_impact(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_LOW)
        assert result.sources[0].impact_level == "MEDIUM"

    def test_boundary_relevance_07_is_MEDIUM(self):
        sources = [{"name": "Ley test", "relevance": 0.70}]
        result = XAIEngine.generate_explanation("Texto.", sources)
        assert result.sources[0].impact_level == "MEDIUM"

    def test_boundary_relevance_071_is_HIGH(self):
        sources = [{"name": "Ley test", "relevance": 0.71}]
        result = XAIEngine.generate_explanation("Texto.", sources)
        assert result.sources[0].impact_level == "HIGH"

    def test_multiple_sources_classified_independently(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_MIX)
        assert len(result.sources) == 2
        assert result.sources[0].impact_level == "HIGH"   # 0.85
        assert result.sources[1].impact_level == "MEDIUM" # 0.40

    def test_empty_sources_returns_empty_list(self):
        result = XAIEngine.generate_explanation("Texto.", [])
        assert result.sources == []

    def test_source_name_preserved(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH)
        assert result.sources[0].source_name == "Constitución Nacional"


class TestXAIEngineReasoningSteps:

    def test_reasoning_steps_always_include_fragment_count(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_MIX)
        assert any("2" in step for step in result.reasoning_steps)

    def test_high_confidence_adds_vectorial_step(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH, confidence_score=0.95)
        texts = " ".join(result.reasoning_steps)
        assert "vectorial" in texts.lower() or "coincidencia" in texts.lower()

    def test_low_confidence_no_vectorial_step(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH, confidence_score=0.85)
        texts = " ".join(result.reasoning_steps)
        assert "Alta coincidencia vectorial" not in texts

    def test_wfd_step_always_present(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH)
        texts = " ".join(result.reasoning_steps)
        assert "WFD" in texts


class TestXAIEngineBiasIntegration:

    def test_bias_pass_adds_neutrality_step(self):
        bias = {"status": "PASS", "political_slant": None}
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH, bias_report=bias)
        texts = " ".join(result.reasoning_steps)
        assert "neutralidad" in texts.lower()

    def test_bias_fail_adds_slant_step(self):
        bias = {"status": "WARN", "political_slant": "LEFT_LEANING"}
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH, bias_report=bias)
        texts = " ".join(result.reasoning_steps)
        assert "sesgo" in texts.lower() or "bias" in texts.lower() or "LEFT_LEANING" in texts

    def test_no_bias_report_defaults_to_neutrality_step(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH, bias_report=None)
        texts = " ".join(result.reasoning_steps)
        assert "neutralidad" in texts.lower()

    def test_bias_summary_stored_in_card(self):
        bias = {"status": "PASS", "score": 0.1}
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH, bias_report=bias)
        assert result.bias_summary == bias

    def test_no_bias_summary_is_none(self):
        result = XAIEngine.generate_explanation("Texto.", SOURCES_HIGH)
        assert result.bias_summary is None
