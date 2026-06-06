import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="secret.env")

api_key = os.getenv("OPENAI_API_KEY")
endpoint = os.getenv("OPENAI_ENDPOINT")
api_version = os.getenv("OPENAI_API_VERSION")
chat_deployment = os.getenv("CHAT_DEPLOYMENT")

url = f"{endpoint}/openai/deployments/{chat_deployment}/chat/completions?api-version={api_version}"

headers = {
    "Content-Type": "application/json",
    "api-key": api_key
}

payload = {
    "messages": [{"role": "user", "content": "Hola, responde brevemente."}],
    "max_tokens": 10
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
