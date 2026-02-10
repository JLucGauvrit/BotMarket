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
    # On utilise la quantité ajustée par le Risk Manager (SÛR)
    qty = state.get("adjusted_qty", 0)
    strategy = state.get("strategy", {})
    entry_price = strategy.get("entry_price", state.get("price"))
    
    if qty < 1:
        return _order_failed("Quantité 0")

    # Protection ultime : Limite de montant théorique ($2000 max par ordre en paper)
    if qty * entry_price > 2000:
        logger.warning(f"⚠️ Ordre trop gros ({qty * entry_price}$), plafonnement.")
        qty = int(2000 / entry_price)

    order = {
        "symbol": symbol,
        "side": "buy",
        "quantity": qty,
        "type": "market", # Market pour garantir l'exécution en paper
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
