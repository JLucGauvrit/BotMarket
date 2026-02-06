import requests
from ..shared.state import AgentState

GATEWAY_URL = "http://gateway:8000"

def execute_trade(state: AgentState):
    decision = state['decision']
    symbol = state['symbol']
    
    if decision == "hold":
        return {}
        
    print(f"⚡ [Executor] Envoi de l'ordre {decision.upper()} vers la Gateway...")
    
    try:
        # On envoie toujours 1 action pour l'instant (Scalping prudent)
        params = {
            "symbol": symbol,
            "side": decision,
            "qty": 1
        }
        resp = requests.post(f"{GATEWAY_URL}/order", params=params, timeout=5)
        
        if resp.status_code == 200:
            print(f"✅ Ordre exécuté avec succès (ID: {resp.json().get('id')})")
        else:
            print(f"❌ Erreur Gateway: {resp.text}")
            
    except Exception as e:
        print(f"❌ Erreur Connection Executor: {e}")
        
    return {}
