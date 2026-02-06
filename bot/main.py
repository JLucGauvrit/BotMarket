import time
import os
from src.orchestrator.graph import build_graph
from src.shared.llm_client import ensure_model_ready

SYMBOL = "GOOGL"

if __name__ == "__main__":
    print("🚀 Démarrage de l'Agent Fédéré...")
    
    # 1. Vérif Modèle
    ensure_model_ready()
    
    # 2. Build du Graph
    bot = build_graph()
    
    # 3. Boucle Infinie
    while True:
        try:
            print(f"\n--- Nouveau Cycle pour {SYMBOL} ---")
            bot.invoke({"symbol": SYMBOL})
            print("--- Cycle terminé, dodo 60s ---")
        except Exception as e:
            print(f"❌ Crash Loop: {e}")
            
        time.sleep(60)
        