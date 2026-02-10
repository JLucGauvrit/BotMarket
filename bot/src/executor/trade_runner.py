"""
Trade Executor V2 - SECURISED
"""

import logging
import requests
from typing import Dict, Any
from ..shared.state import AgentState

logger = logging.getLogger("executor")
GATEWAY_URL = "http://gateway:8000"

def execute_trade(state: AgentState) -> Dict[str, Any]:
    """
    Agent d'exécution sécurisé.
    """
    symbol = state.get('symbol', 'UNKNOWN')
    decision = state.get('decision', 'hold')
    approved = state.get('approved', False)
    
    # --- CIRCUIT BREAKER EXECUTOR ---
    current_price = state.get('price', 0)
    if decision != "hold" and current_price <= 0:
        logger.critical(f"⛔ [Executor] ABORT: Prix invalide ({current_price}) pour {symbol}")
        return {"executed": False, "reason": "SAFETY: Prix invalide"}
    # --------------------------------

    print(f"🚀 [Executor] Exécution pour {symbol} - {decision.upper()}...")
    
    if decision == "hold" or not approved:
        return {"executed": False, "reason": "HOLD ou rejeté"}
    
    if decision == "buy":
        return _execute_buy(symbol, state)
    elif decision == "sell":
        return _execute_sell(symbol, state)
        
    return {"executed": False}

def _execute_buy(symbol: str, state: AgentState) -> Dict[str, Any]:
    """
    Exécute un achat avec dimensionnement dynamique (5% du cash).
    """
    # 1. On récupère le cash disponible
    # Si 'cash' n'est pas dans le state, on met une valeur par défaut élevée pour tester
    cash = state.get("cash", 0.0)
    if cash <= 0: 
        cash = 10000.0 # Fallback de sécurité

    strategy = state.get("strategy", {})
    # Sécurité prix
    entry_price = strategy.get("entry_price", state.get("price"))
    if not entry_price or entry_price <= 0:
        entry_price = state.get("price", 0)

    if entry_price <= 0:
        return _order_failed(f"Prix invalide pour {symbol}")

    # --- 2. CALCUL DE LA TAILLE DE POSITION (Dynamic Sizing) ---
    # On investit 5% du cash disponible par trade
    # Avec 91k$, cela fera des ordres de ~4 550$
    allocation_pct = 0.05
    target_amount = cash * allocation_pct
    
    # On calcule la quantité
    qty = int(target_amount / entry_price)
    
    # Gestion des petits prix (Penny stocks / Crypto)
    if qty < 1:
        # Si c'est une crypto fractionnable, on pourrait laisser le float
        # Pour Alpaca Stock, il faut souvent un int, sauf si fractionable activé
        if entry_price < 1.0: 
             # Pour les actifs < 1$, on s'assure d'en prendre au moins 1
             qty = 1
        else:
             return _order_failed(f"Montant {target_amount}$ insuffisant pour prix {entry_price}$")

    print(f"🚀 [Executor] CALIBRATION: Cash={cash}$ | Target={target_amount}$ | Qty={qty}")

    # --- 3. ENVOI DE L'ORDRE ---
    order = {
        "symbol": symbol,
        "side": "buy",
        "quantity": qty,
        "type": "market",
        "time_in_force": "day"
    }
    
    return _send_order(order)

def _execute_sell(symbol: str, state: AgentState) -> Dict[str, Any]:
    qty = state.get("adjusted_qty", 0)
    if qty < 1: return _order_failed("Rien à vendre")
    
    order = {
        "symbol": symbol,
        "side": "sell",
        "quantity": qty,
        "type": "market",
        "time_in_force": "day"
    }
    return _send_order(order)

def _send_order(order: Dict) -> Dict:
    try:
        resp = requests.post(f"{GATEWAY_URL}/orders", json=order, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"✅ Ordre envoyé: {data.get('order_id')}")
            return {"executed": True, "order_id": data.get("order_id")}
        else:
            return _order_failed(f"Gateway: {resp.text}")
    except Exception as e:
        return _order_failed(str(e))

def _order_failed(reason: str):
    logger.error(f"❌ Echec ordre: {reason}")
    return {"executed": False, "reason": reason}
