import os
import time
import json
import requests
from typing import TypedDict, Literal
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

# Configuration
GATEWAY_URL = "http://gateway:8000"
OLLAMA_HOST = "http://ollama:11434"
SYMBOL = "AAPL"  # Actif à trader pour le test

model_name = os.getenv("MODEL", "qwen2.5:1.5b")

def ensure_model_is_ready(model_name="qwen2.5:1.5b"):
    ollama_url = "http://ollama:11434/api/pull"
    print(f"🤖 Vérification du modèle {model_name}...")
    try:
        response = requests.post(ollama_url, json={"name": model_name}, stream=True)
        for line in response.iter_lines():
            if line:
                status = json.loads(line)
                if 'status' in status:
                    print(f"Ollama: {status['status']}")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation du modèle : {e}")

# 1. Définition de la Mémoire de l'Agent (State)
class AgentState(TypedDict):
    symbol: str
    price: float
    position: int
    analysis: str
    decision: Literal["buy", "sell", "hold"]

# --- NOEUD 1 : Récupération des Données ---
def get_market_data(state: AgentState):
    print(f"📡 [Data] Récupération données pour {state['symbol']}...")
    try:
        # On demande le prix (via les positions ou une API de prix si tu en as une)
        # Pour l'exemple, on simule une récupération via les positions gateway
        positions = requests.get(f"{GATEWAY_URL}/positions").json()
        current_qty = 0
        current_price = 0.0
        
        # Simulation simplifiée : on cherche si on a déjà du stock
        for pos in positions:
            if pos['symbol'] == state['symbol']:
                current_qty = int(pos['qty'])
                current_price = float(pos['current_price'])
        
        # Si pas de position, on a besoin d'un prix (ici on mock ou on ajoute un endpoint price)
        if current_price == 0:
            current_price = 150.0  # Valeur par défaut pour tester si pas de data
            
        return {"price": current_price, "position": current_qty}
    except Exception as e:
        print(f"❌ Erreur Data: {e}")
        return {"price": 0.0}

# --- NOEUD 2 : L'Analyste (Ollama) ---
def market_analyst(state: AgentState):
    print(f"🧠 [Analyst] Réflexion sur {state['symbol']} à ${state['price']}...")
    
    llm = ChatOllama(
        base_url=OLLAMA_HOST, 
        model=model_name, 
        temperature=0
    )
    
    prompt = f"""
    Tu es un trader expert. Le prix actuel de {state['symbol']} est de {state['price']}$.
    Tu as actuellement {state['position']} actions.
    
    Règle:
    - Si prix < 145: ACHETER (buy)
    - Si prix > 155: VENDRE (sell)
    - Sinon: ATTENDRE (hold)
    
    Réponds UNIQUEMENT par un mot : 'buy', 'sell', ou 'hold'.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    decision = response.content.strip().lower()
    
    # Nettoyage basique de la réponse du LLM
    if "buy" in decision: decision = "buy"
    elif "sell" in decision: decision = "sell"
    else: decision = "hold"
        
    print(f"💡 [Analyst] Décision : {decision.upper()}")
    return {"decision": decision, "analysis": response.content}

# --- NOEUD 3 : L'Exécuteur ---
def trade_executor(state: AgentState):
    decision = state['decision']
    qty = 1
    
    if decision == "hold":
        return {}
        
    print(f"⚡ [Executor] Envoi ordre {decision.upper()}...")
    try:
        requests.post(
            f"{GATEWAY_URL}/order", 
            params={"symbol": state['symbol'], "side": decision, "qty": qty}
        )
    except Exception as e:
        print(f"❌ Erreur Execution: {e}")
        
    return {}

# 4. Construction du Graphe
workflow = StateGraph(AgentState)

# Ajout des noeuds
workflow.add_node("get_data", get_market_data)
workflow.add_node("analyst", market_analyst)
workflow.add_node("executor", trade_executor)

# Définition du flux
workflow.set_entry_point("get_data")
workflow.add_edge("get_data", "analyst")
workflow.add_edge("analyst", "executor")
workflow.add_edge("executor", END)

# Compilation
app = workflow.compile()

# 5. Boucle Principale
if __name__ == "__main__":
    print("🤖 Démarrage du Cerveau LangGraph...")

    target_model = os.getenv("MODEL", "qwen2.5:1.5b")
    ensure_model_is_ready(target_model)
    
    time.sleep(5) # Warmup
    
    while True:
        try:
            # Invocation du graphe
            app.invoke({"symbol": SYMBOL})
            print("--- Cycle terminé, pause 60s ---")
        except Exception as e:
            print(f"❌ Erreur critique : {e}")
            
        time.sleep(60)
        