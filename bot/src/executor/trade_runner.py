import requests
import logging
import math
from ..shared.state import AgentState

GATEWAY_URL = "http://gateway:8000"
logger = logging.getLogger("executor")

def execute_trade(state: AgentState):
    decision = state['decision']
    raw_symbol = state['symbol']
    price = state.get('price', 0.0)
    
    if decision not in ["buy", "sell"]:
        return {}
        
    # --- 1. Mapping Alpaca ---
    symbol_map = {"SHIBA_INU": "SHIB", "DOGE": "DOGE", "BITCOIN": "BTC", "ETHEREUM": "ETH"}
    clean_name = raw_symbol.replace("-USD", "").upper()
    ticker = symbol_map.get(clean_name, clean_name)
    
    # Suffixe Crypto Alpaca
    if ticker in ["BTC", "ETH", "DOGE", "SHIB", "SOL", "LTC"]:
        ticker = f"{ticker}/USD"

    # --- 2. Calcul de la Quantité (Sécurisé) ---
    target_usd = 25.0 # On vise 25$ pour être large au-dessus des 10$ min
    
    if price > 0:
        # Cas idéal : on connait le prix
        qty = math.ceil(target_usd / price)
    else:
        # Cas Secours (Si le Retriever a échoué à trouver le prix)
        # On augmente drastiquement les doses pour éviter l'erreur 40310000
        if "SHIB" in ticker:
            qty = 3_000_000  # ~55$ (Marge de sécurité énorme)
        elif "DOGE" in ticker:
            qty = 300        # ~30$
        else:
            qty = 1          # Actions classiques

    print(f"⚡ [Executor] ENVOI : {decision.upper()} {qty} x {ticker} (Prix ref: {price})")
    
    try:
        # Utilisation de params= pour la Gateway
        payload = {
            "symbol": ticker,
            "side": decision,
            "qty": int(qty),
            "type": "market",
            "time_in_force": "gtc"
        }
        
        resp = requests.post(f"{GATEWAY_URL}/order", params=payload, timeout=10)
        
        if resp.status_code == 200:
            print(f"✅ ORDRE RÉUSSI : {ticker} (ID: {resp.json().get('id')})")
            return {"last_order_id": resp.json().get('id')}
        else:
            # On log l'erreur pour comprendre
            print(f"❌ REJET ALPACA : {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"❌ ERREUR CONNEXION : {e}")
        
    return {}
