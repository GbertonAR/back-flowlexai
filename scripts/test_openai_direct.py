## 🐍 PROTOCOLO DE IDENTIDAD .PY
"""
SISTEMA: FlowState AI - Inteligencia Conectada 
MÓDULO: test_openai_direct.py
PROPIEDAD INTELECTUAL: (c) 2026 FlowState AI
AUTOR: Gustavo Berton
-------------------------------------------------------
DESCRIPCIÓN: Script para probar la conexión directa con Azure OpenAI usando el cliente oficial de openai.
FECHA CREACIÓN: 2026-03-25
ÚLTIMA MODIFICACIÓN: 2026-03-25
REF. TICKET: #FS-011-RAG
"""

import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path="secret.env")

client = AzureOpenAI(
  api_key = os.getenv("OPENAI_API_KEY"),  
  api_version = os.getenv("OPENAI_API_VERSION"),
  azure_endpoint = os.getenv("OPENAI_ENDPOINT")
)

def test():
    print(f"Testing endpoint: {os.getenv('OPENAI_ENDPOINT')}")
    print(f"API Version: {os.getenv('OPENAI_API_VERSION')}")
    
    # Intentar con un nombre común si el del env falla
    deployments_to_try = [
        os.getenv("EMBEDDING_DEPLOYMENT"),
        "text-embedding-ada-002",
        "embedding",
        "ada-002",
        "text-embedding-3-small"
    ]
    
    for dep in deployments_to_try:
        if not dep: continue
        print(f"\n--- Trying deployment: {dep} ---")
        try:
            response = client.embeddings.create(
                input="test",
                model=dep
            )
            print(f"SUCCESS with {dep}!")
            print(f"Dimensions: {len(response.data[0].embedding)}")
            return
        except Exception as e:
            print(f"Failed with {dep}: {e}")

if __name__ == "__main__":
    test()
