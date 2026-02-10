"""
Risk Validator Agent V2 - SECURISED
"""

import logging
from typing import Dict, Any
import requests
from ..shared.state import AgentState

logger = logging.getLogger("risk_validator")

GATEWAY_URL = "http://gateway:8000"

# Limites de risque
MAX_SINGLE_POSITION_RISK_PCT = 0.02
MAX_DAILY_LOSS_PCT = 0.05
MIN_POSITION_VALUE = 50
MAX_POSITION_COUNT = 10

def validate_strategy(state: AgentState) -> Dict[str, Any]:
    """Agent principal: valide stratégie avant exécution."""
    
    symbol = state.get('symbol', 'UNKNOWN')
    strategy = state.get('strategy', {})
    decision = state.get('decision', 'hold')
    
    # --- CIRCUIT BREAKER: PRIX INVALIDE ---
    # Empêche le "Fat Finger" sur BTC si le prix est 0
    current_price = state.get('price', 0.0)
    if current_price <= 0 and decision != "hold":
        logger.critical(f"🛑 SAFETY ABORT: Tentative de trade sur {symbol} avec PRIX=0 !")
        return _reject(f"CRITICAL: Prix invalide ({current_price}$). Trading bloqué.")
    # --------------------------------------

    print(f"🛡️ [Risk Validator] Validation de {symbol} (Prix ref: {current_price}$)...")
    
    if decision == "hold":
        return {
            "approved": True,
            "decision": "hold",
            "reason": "HOLD - pas de validation requise",
            "adjusted_qty": 0
        }
    
    # Récupère infos du portefeuille
    try:
        acct_resp = requests.get(f"{GATEWAY_URL}/account", timeout=2)
        if acct_resp.status_code != 200:
            return _reject("Erreur gateway - account data")
        
        account_data = acct_resp.json()
        cash = float(account_data.get("cash", 0))
        portfolio_value = float(account_data.get("portfolio_value", 0))
        
        pos_resp = requests.get(f"{GATEWAY_URL}/positions", timeout=2)
        if pos_resp.status_code != 200:
            return _reject("Erreur gateway - positions data")
        
        positions = pos_resp.json()
        open_positions = len(positions)
    
    except Exception as e:
        logger.error(f"❌ Erreur retrieval data: {e}")
        return _reject(f"Erreur données: {e}")
    
    # ====== VALIDATIONS ======
    validations = []
    
    # 1. DECISION = BUY
    if decision == "buy":
        
        entry_price = strategy.get("entry_price", current_price)
        # Sécurité supplémentaire sur le prix d'entrée
        if entry_price <= 0: entry_price = current_price

        position_size = strategy.get("position_size", 0)
        
        # 1a. Cash suffisant?
        required_cash = entry_price * position_size
        
        if cash < required_cash * 1.05:
            # Réduit la position size
            adjusted_size = int((cash * 0.95) / entry_price) if entry_price > 0 else 0
            
            if adjusted_size < 1:
                return _reject(f"Cash insuffisant: {cash:.2f}$ < {required_cash:.2f}$")
            
            validations.append(f"⚠️ Cash limité: Réduit position {position_size} → {adjusted_size}")
            position_size = adjusted_size
        
        # 1b. Risk par position < 2%
        if portfolio_value > 0:
            risk_pct = (entry_price * position_size) / portfolio_value
            # Note: Calcul simplifié d'exposition ici, pour être plus strict
            
            if risk_pct > MAX_SINGLE_POSITION_RISK_PCT * 2: # Tolérance x2 pour crypto
                max_qty = int((portfolio_value * MAX_SINGLE_POSITION_RISK_PCT * 2) / entry_price)
                if max_qty < position_size:
                    validations.append(f"⚠️ Exposition élevée. Réduit {position_size} → {max_qty}")
                    position_size = max_qty

        # 1c. Valeur position minimale
        position_value = entry_price * position_size
        if position_value < MIN_POSITION_VALUE:
            return _reject(f"Position trop petite: {position_value:.2f}$ < {MIN_POSITION_VALUE}$")
        
        # 1d. Max positions
        if open_positions >= MAX_POSITION_COUNT:
            return _reject(f"Portfolio saturé: {open_positions} positions")

        if position_size < 1:
            return _reject("Position ajustée à 0 - rejet")
        
        return {
            "approved": True,
            "decision": "buy",
            "reason": "BUY strategy approuvée",
            "adjusted_qty": position_size,
            "cash_available": cash,
            "portfolio_value": portfolio_value,
            "validations": validations,
            "strategy": strategy
        }
    
    # 2. DECISION = SELL
    elif decision == "sell":
        # Vérification qu'on possède bien l'actif
        existing_qty = 0
        for pos in positions:
            if pos['symbol'] == symbol:
                existing_qty = int(float(pos['qty']))
                break
        
        if existing_qty <= 0:
            return _reject(f"Pas de position à vendre: {symbol}")
            
        return {
            "approved": True,
            "decision": "sell",
            "reason": "SELL strategy approuvée",
            "adjusted_qty": existing_qty,
            "strategy": strategy
        }
    
    return _reject("Décision inconnue")

def _reject(reason: str) -> Dict[str, Any]:
    logger.warning(f"🛑 Risk validation REJECT: {reason}")
    return {
        "approved": False,
        "decision": "rejected",
        "reason": f"RISK REJECT: {reason}",
        "adjusted_qty": 0
    }
