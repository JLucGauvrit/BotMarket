import time
import requests
import logging
from src.orchestrator.graph import build_graph
from src.shared.llm_client import ensure_model_ready
from src.agents.discovery import DiscoveryAgent

GATEWAY_URL = "http://gateway:8000"

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
            # -- PHASE 0 : VERIFICATION PRÉLIMINAIRE --
            current_positions = []
            try:
                pos_resp = requests.get(f"{GATEWAY_URL}/positions", timeout=2)
                if pos_resp.status_code == 200:
                    current_positions = [p['symbol'] for p in pos_resp.json()]
            except: 
                pass

            # --- PHASE 1 : DÉCOUVERTE ---
            print("\n📡 --- Lancement du SCAN MARCHÉ ---")
            new_targets = discovery.scan_market()
            
            # On fusionne les listes (On veut gérer nos positions + analyser les nouvelles)
            # set() évite les doublons
            all_symbols_to_process = list(set(current_positions + new_targets))
            
            print(f"🎯 Liste de travail : {all_symbols_to_process} (Positions: {len(current_positions)} | News: {len(new_targets)})")

            for symbol in all_symbols_to_process:
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
    