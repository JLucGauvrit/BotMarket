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
    Vérifie si le modèle est présent sur le serveur Ollama.
    S'il est absent, lance le téléchargement (pull) automatiquement.
    Bloque l'exécution jusqu'à ce que le modèle soit prêt.
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
    Factory qui retourne une instance ChatOllama configurée.
    Utilisée par tous les agents (Analyste, Sentiment, etc.).
    """
    return ChatOllama(
        base_url=DEFAULT_OLLAMA_HOST,
        model=model_name,
        temperature=temperature,
        # 'keep_alive' garde le modèle en VRAM (ex: 1h) pour éviter 
        # de le recharger à chaque cycle (Crucial pour la performance)
        keep_alive="1h"
    )
