import requests
from ..shared.state import AgentState

GATEWAY_URL = "http://gateway:8000"

def get_market_data(state: AgentState):
    print(f"📡 [Retriever] Récupération des données pour {state['symbol']}...")
    
    try:
        # 1. Récupération des positions
        pos_resp = requests.get(f"{GATEWAY_URL}/positions", timeout=2)
        positions = pos_resp.json() if pos_resp.status_code == 200 else []
        
        # 2. Récupération du compte (pour le cash)
        acct_resp = requests.get(f"{GATEWAY_URL}/account", timeout=2)
        account = acct_resp.json() if acct_resp.status_code == 200 else {}
        
        # Extraction
        qty = 0
        current_price = 0.0
        
        # On cherche si on a déjà l'actif
        for pos in positions:
            if pos['symbol'] == state['symbol']:
                qty = int(pos['qty'])
                current_price = float(pos['current_price'])
                
        # Fallback : Si on n'a pas de position, on devrait appeler un endpoint de prix
        # (Pour l'instant on simule un prix si l'API ne le donne pas via positions)
        if current_price == 0:
            current_price = 150.0 # TODO: Créer un endpoint /price/{symbol} dans la Gateway
            
        return {
            "position_qty": qty,
            "price": current_price,
            "cash": float(account.get("cash", 0.0))
        }
        
    except Exception as e:
        print(f"❌ Erreur Retriever: {e}")
        # Valeurs de sécurité pour ne pas faire planter le graphe
        return {"position_qty": 0, "price": 0.0, "cash": 0.0}
    