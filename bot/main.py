import time
import logging
from src.orchestrator.graph import build_graph
from src.shared.llm_client import ensure_model_ready
from src.agents.discovery import DiscoveryAgent # <-- Import du nouvel agent

# Configuration Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def run_bot():
    print("🚀 Démarrage du Bot Chasseur d'Opportunités...")
    ensure_model_ready()
    
    # Initialisation
    discovery = DiscoveryAgent()
    bot_graph = build_graph()
    
    while True:
        try:
            # --- PHASE 1 : DÉCOUVERTE ---
            print("\n📡 --- Lancement du SCAN MARCHÉ ---")
            targets = discovery.scan_market()
            
            if not targets:
                print("⚠️ Aucune cible trouvée, on attend...")
                time.sleep(60)
                continue

            # --- PHASE 2 : ANALYSE & TRADING ---
            print(f"🎯 Cibles verrouillées pour ce cycle : {targets}")
            
            for symbol in targets:
                print(f"\n⚡ Traitement de : {symbol}")
                try:
                    # On invoque le graphe LangGraph pour ce symbole spécifique
                    # Le graphe va faire : Retriever -> Social -> Analyst -> Trader
                    result = bot_graph.invoke({"symbol": symbol})
                    
                    decision = result.get("decision", "unknown")
                    print(f"   🏁 Résultat {symbol} : {decision}")
                    
                except Exception as e:
                    print(f"   ❌ Erreur sur {symbol}: {e}")
                
                # Petite pause entre chaque symbole pour ne pas spammer les API
                time.sleep(5)

            # --- PHASE 3 : REPOS ---
            print("\n💤 Fin de la ronde. Pause de 5 minutes avant prochain scan.")
            time.sleep(300) # 5 minutes de pause

        except KeyboardInterrupt:
            print("🛑 Arrêt manuel du bot.")
            break
        except Exception as e:
            print(f"❌ Crash Critique Loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()
    