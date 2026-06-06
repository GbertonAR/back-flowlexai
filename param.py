import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

# Valores obtenidos de tu comando 'az cognitiveservices account list'
SUBSCRIPTION_ID = "b82727bc-d03b-4da8-a8f7-3c022b910999" 
RESOURCE_GROUP = "rg-flowstateai" 
ACCOUNT_NAME = "ai-flowlex" 

def update_env_file(key, value):
    env_path = ".env"
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    
    updated = False
    with open(env_path, "w") as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                updated = True
            else:
                f.write(line)
        if not updated:
            f.write(f"{key}={value}\n")

def get_embedding_deployment():
    try:
        credential = DefaultAzureCredential()
        client = CognitiveServicesManagementClient(credential, SUBSCRIPTION_ID)
        
        # Listamos todos los despliegues para ver qué nombres tienen realmente
        deployments = client.deployments.list(RESOURCE_GROUP, ACCOUNT_NAME)
        
        print("--- Despliegues encontrados ---")
        for d in deployments:
            model_name = d.properties.model.name.lower()
            print(f"Despliegue: {d.name} | Modelo: {model_name}")
            
            # Buscamos 'embedding' o 'ada' (común en modelos de vectores antiguos)
            if "embedding" in model_name or "ada" in model_name:
                return d.name
        print("-------------------------------")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    print("🔍 Consultando recursos en ai-flowlex...")
    deployment = get_embedding_deployment()
    
    if deployment:
        print(f"✅ Identificado: {deployment}")
        update_env_file("EMBEDDING_DEPLOYMENT", deployment)
        print("💾 Guardado en .env")
    else:
        print("⚠️ No se detectó un modelo de embeddings. Revisa la lista de arriba.")