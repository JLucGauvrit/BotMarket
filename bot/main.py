import requests
import time
from typing import TypedDict
from langgraph.graph import StateGraph, END

# Configuration
GATEWAY_URL = "http://gateway:8000"
OLLAMA_HOST = "http://ollama:11434"

# 1. Définition de l'état
class AgentState(TypedDict):
    symbol: str
    decision: str

# 2. Nodes (Les actions)
def market_analyst(state: AgentState):
    print(f"--- Analyse de {state['symbol']} ---")
    # Simulation d'analyse (ici tu appelleras Ollama plus tard)
    # Pour le test, on alterne.
    return {"decision": "buy"}

def execution_trader(state: AgentState):
    decision = state['decision']
    symbol = state['symbol']
    
    if decision in ["buy", "sell"]:
        print(f"--- Exécution Ordre : {decision.upper()} {symbol} via Gateway ---")
        try:
            # Appel à TA Gateway, pas à Alpaca direct !
            resp = requests.post(f"{GATEWAY_URL}/order", params={"symbol": symbol, "side": decision, "qty": 1})
            print(f"Réponse Gateway: {resp.status_code}")
        except Exception as e:
            print(f"Erreur Gateway: {e}")
    return state

# 3. Construction du Graphe
workflow = StateGraph(AgentState)
workflow.add_node("analyst", market_analyst)
workflow.add_node("trader", execution_trader)

workflow.set_entry_point("analyst")
workflow.add_edge("analyst", "trader")
workflow.add_edge("trader", END)

app = workflow.compile()

# 4. Boucle principale (Main Loop)
if __name__ == "__main__":
    print("Démarrage du Cerveau...")
    # Attendre que la Gateway et Ollama soient prêts
    time.sleep(5) 
    
    while True:
        app.invoke({"symbol": "BTC/USD", "decision": "wait"})
        time.sleep(60) # Pause de 1 minute entre les cycles
        