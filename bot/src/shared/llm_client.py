import os
import requests
import json
import logging
from langchain_ollama import ChatOllama

# Configuration des logs pour voir ce qui se passe dans Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_client")

# Configuration par défaut via les variables d'environnement
# Cela permet de changer de modèle sans toucher au code (juste via le .env ou docker-compose)
DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("MODEL", "qwen2.5:1.5b")

def ensure_model_ready(model_name: str = DEFAULT_MODEL, base_url: str = DEFAULT_OLLAMA_HOST):
    """
    Ensure the specified Ollama model is available and ready.

    This function checks the Ollama server for the presence of `model_name` and,
    if absent, requests a pull. It blocks until the model is detected as
    available (or until the pull process completes/raises). Used by agents to
    guarantee the LLM is ready before making inference requests.

    Args:
        model_name (str): Name of the model to verify (ex: "qwen2.5:1.5b").
        base_url (str): Base URL of the Ollama server (ex: "http://ollama:11434").

    Returns:
        None: This function does not return a value; it ensures readiness as a side effect.

    Effects:
        - Performs HTTP GET to `{base_url}/api/tags` to list available models.
        - If model missing, performs HTTP POST to `{base_url}/api/pull` to download it.
        - Emits logs (info/warning/error) on progress and failures.
    """
    logger.info(f"🤖 Vérification de la disponibilité du modèle '{model_name}'...")

    try:
        # 1. On vérifie d'abord si le modèle est déjà chargé (Optimisation)
        tags_url = f"{base_url}/api/tags"
        resp = requests.get(tags_url, timeout=5)
        
        if resp.status_code == 200:
            existing_models = [m['name'] for m in resp.json().get('models', [])]
            # On vérifie si notre modèle est dans la liste (ex: "qwen2.5:1.5b")
            # On gère le cas où le tag ":latest" est implicite
            if any(model_name in m for m in existing_models):
                logger.info(f"✅ Modèle '{model_name}' détecté et prêt.")
                return

    except Exception as e:
        logger.warning(f"⚠️ Impossible de contacter Ollama pour vérifier les tags: {e}")

    # 2. Si le modèle n'est pas trouvé, on le télécharge
    pull_url = f"{base_url}/api/pull"
    logger.info(f"⬇️ Modèle absent. Téléchargement de '{model_name}' en cours... (Cela peut prendre du temps)")
    
    try:
        # stream=True permet de ne pas bloquer indéfiniment sans nouvelles
        with requests.post(pull_url, json={"name": model_name}, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if 'status' in data:
                        # On logue seulement les étapes importantes pour ne pas spammer
                        status = data['status']
                        if status == "success":
                            logger.info(f"🎉 Téléchargement de {model_name} terminé !")
                        elif "downloading" in status and "total" not in data:
                            # Log léger pour dire qu'on travaille
                            pass
                            
    except Exception as e:
        logger.error(f"❌ Échec critique du téléchargement du modèle : {e}")
        # On ne raise pas forcément ici, on laisse LangChain essayer et échouer proprement plus tard
        
def get_llm(model_name: str = DEFAULT_MODEL, temperature: float = 0):
    """
    Return a configured ChatOllama instance for inference.

    This factory centralizes LLM client configuration so that agents share the
    same base URL, model selection and temperature. The returned object is
    suitable for prompt-based chat completions via LangChain integrations.

    Args:
        model_name (str): Model identifier to use (defaults to `DEFAULT_MODEL`).
        temperature (float): Sampling temperature for generation (0 = deterministic).

    Returns:
        ChatOllama: Configured chat client instance wired to `DEFAULT_OLLAMA_HOST`.

    Effects:
        - No network calls are performed by this factory itself, but the returned
          `ChatOllama` instance will use `DEFAULT_OLLAMA_HOST` when invoking the LLM.
    """
    return ChatOllama(
        base_url=DEFAULT_OLLAMA_HOST,
        model=model_name,
        temperature=temperature,
        # 'keep_alive' garde le modèle en VRAM (ex: 1h) pour éviter 
        # de le recharger à chaque cycle (Crucial pour la performance)
        keep_alive="1h"
    )
