## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: llm.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Cliente centralizado de LLM (Azure OpenAI) para LexIA. 
             Maneja autenticación, reintentos y logging forense.
FECHA CREACIÓN: 2026-03-15
ÚLTIMA MODIFICACIÓN: 2026-05-06
REF. TICKET: #FS-014-LLM
"""

import hashlib
import numpy as np
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.embeddings import Embeddings
from app.core.config import settings
from app.core.logger import forensic_log as logger
from app.core.health import health_monitor


def _get_token_provider():
    """Retorna un token provider de Managed Identity para Azure Cognitive Services."""
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    credential = DefaultAzureCredential()
    return get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

class MockChatModel:
    """Modelo de chat de emergencia para cuando no hay despliegues activos."""
    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        return AIMessage(content="[MOCK RESPONSE] El sistema está en modo soberano simplificado. No se detectó despliegue de Chat en Azure.")
    
    async def ainvoke(self, messages: list[BaseMessage]) -> AIMessage:
        return AIMessage(content="[MOCK RESPONSE] El sistema está en modo soberano simplificado. No se detectó despliegue de Chat en Azure.")

class DeterministicMockEmbedding(Embeddings):
    """Genera vectores deterministas basados en el hash del texto para pruebas RAG sin costo."""
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        hash_val = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))
        return np.random.uniform(-0.1, 0.1, 1536).tolist()

class LLMService:
    """
    Servicio centralizado para interactuar con Azure OpenAI.
    Gestiona modelos de Chat (GPT) y Embeddings (ada-002).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Inicialización de Chat
        try:
            is_cloud_ok = health_monitor.status["services"].get("azure_cloud", True)

            if settings.CHAT_DEPLOYMENT and is_cloud_ok:
                auth_mode = "Managed Identity" if settings.USE_MANAGED_IDENTITY else "API Key"
                logger.info(f"🧠 [WORKFLOW] Auth Azure OpenAI → {auth_mode}")

                common_kwargs = dict(
                    azure_deployment=settings.CHAT_DEPLOYMENT,
                    openai_api_version=settings.OPENAI_API_VERSION,
                    azure_endpoint=settings.OPENAI_ENDPOINT,
                    temperature=0.0,
                )
                if settings.USE_MANAGED_IDENTITY:
                    common_kwargs["azure_ad_token_provider"] = _get_token_provider()
                else:
                    common_kwargs["api_key"] = settings.OPENAI_API_KEY

                self.chat_client = AzureChatOpenAI(**common_kwargs)
                logger.info(f"✅ [OK] Chat Model listo: {settings.CHAT_DEPLOYMENT}")
            else:
                self.chat_client = MockChatModel()
                logger.warning("⚠️ [WARNING] CHAT_DEPLOYMENT no configurado. Usando MockChatModel.")
        except Exception as e:
            logger.error(f"❌ [FAULT] Fallo en Chat Model: {e}. Usando MockChatModel.")
            self.chat_client = MockChatModel()

        # Inicialización de Embeddings con Auto-Mock Fallback
        try:
            if settings.EMBEDDING_DEPLOYMENT:
                embed_kwargs = dict(
                    azure_deployment=settings.EMBEDDING_DEPLOYMENT,
                    openai_api_version=settings.OPENAI_API_VERSION,
                    azure_endpoint=settings.OPENAI_ENDPOINT,
                )
                if settings.USE_MANAGED_IDENTITY:
                    embed_kwargs["azure_ad_token_provider"] = _get_token_provider()
                else:
                    embed_kwargs["api_key"] = settings.OPENAI_API_KEY

                self.embed_client = AzureOpenAIEmbeddings(**embed_kwargs)
                logger.info(f"✅ [OK] Embeddings Azure configurados: {settings.EMBEDDING_DEPLOYMENT}")
            else:
                raise ValueError("EMBEDDING_DEPLOYMENT vacío")
        except Exception:
            logger.warning("🧠 [WORKFLOW] Usando DeterministicMockEmbedding (Modo ahorro de tokens).")
            self.embed_client = DeterministicMockEmbedding()

        self._initialized = True
        logger.info("✅ [OK] LLMService centralizado inicializado.")

    def get_chat_model(self, temperature: float = 0.0):
        if temperature != 0.0 and self.chat_client:
            kwargs = dict(
                azure_deployment=settings.CHAT_DEPLOYMENT,
                openai_api_version=settings.OPENAI_API_VERSION,
                azure_endpoint=settings.OPENAI_ENDPOINT,
                temperature=temperature,
            )
            if settings.USE_MANAGED_IDENTITY:
                kwargs["azure_ad_token_provider"] = _get_token_provider()
            else:
                kwargs["api_key"] = settings.OPENAI_API_KEY
            return AzureChatOpenAI(**kwargs)
        return self.chat_client

    def get_embeddings(self):
        return self.embed_client

llm_service = LLMService()
