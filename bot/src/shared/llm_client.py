import os
import logging
from langchain_openrouter import ChatOpenRouter  # pip install langchain-openrouter

# Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_client")

# Config par défaut via variables d'environnement
# ex: OPENROUTER_API_KEY=sk-or-v1-...
DEFAULT_OPENROUTER_MODEL = os.getenv("MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY n'est pas défini dans l'environnement."
    )

def ensure_model_ready(model_name: str = DEFAULT_OPENROUTER_MODEL):
    """
    Pour OpenRouter, il n'y a pas de 'pull' de modèle côté client.
    On se contente de loguer le modèle utilisé.
    """
    logger.info(f"🤖 Utilisation du modèle OpenRouter '{model_name}' via API distante.")


def get_llm(model_name: str = DEFAULT_OPENROUTER_MODEL, temperature: float = 0):
    """
    Retourne une instance ChatOpenRouter configurée pour OpenRouter.
    """
    return ChatOpenRouter(
        model=model_name,
        api_key=OPENROUTER_API_KEY,
        # Base URL officielle OpenRouter
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
    )
