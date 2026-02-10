"""
Risk Validator Agent V2 - SECURISED & CLEANED
"""

import logging
from typing import Dict, Any
import requests
from ..shared.state import AgentState

logger = logging.getLogger("risk_validator")

GATEWAY_URL = "http://gateway:8000"

# --- CONFIGURATION DES LIMITES ---
MAX_POS_EXPOSURE_PCT = 0.20  # Max 20% du portfolio sur un seul actif (Mode Hunter)
MAX_DAILY_LOSS_PCT = 0.05    # Stop si perte journalière > 5%
MIN_POSITION_VALUE = 20      # On baisse un peu pour accepter les petits tests
MAX_POSITION_COUNT = 15      # Jusqu'à 15 lignes

def validate_strategy(state: AgentState) -> Dict[str, Any]:
    """Agent principal: valide stratégie avant exécution."""
    
    symbol = state.get('symbol', 'UNKNOWN')
    strategy = state.get('strategy', {})
    decision = state.get('decision', 'hold')
    
    # --- CIRCUIT BREAKER: PRIX INVALIDE ---
    # Empêche le "Fat Finger" si le prix est 0 ou négatif
    current_price = state.get('price', 0.0)
    if current_price <= 0 and decision != "hold":
        logger.critical(f"🛑 SAFETY ABORT: Tentative de trade sur {symbol} avec PRIX={current_price} !")
        return _reject(f"CRITICAL: Prix invalide ({current_price}$). Trading bloqué.")
    # --------------------------------------

    print(f"🛡️ [Risk Validator] Validation de {symbol} (Prix ref: {current_price}$)...")
    
    # Pas de validation nécessaire pour un HOLD
    if decision == "hold":
        return {
            "approved": True,
            "decision": "hold",
            "reason": "HOLD - pas de validation requise",
            "adjusted_qty": 0
        }
    
    # Récupération des données du portefeuille
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
        # Sécurité : si la stratégie n'a pas mis de prix, on prend le prix actuel
        if entry_price <= 0: entry_price = current_price

        # Quantité demandée par la stratégie (si définie)
        position_size = strategy.get("position_size", 0)
        
        # Si la stratégie n'a pas défini de taille (cas fréquent si l'Executor gère le sizing),
        # on simule une taille de 5% du cash pour les vérifications de risque
        if position_size == 0 and entry_price > 0:
            simulated_investment = cash * 0.05
            position_size = int(simulated_investment / entry_price)

        # 1a. Cash suffisant ?
        required_cash = entry_price * position_size
        
        if cash < required_cash:
            # On tente de réduire la taille pour que ça passe
            max_affordable_qty = int(cash * 0.95 / entry_price) # Marge de 5%
            
            if max_affordable_qty < 1:
                return _reject(f"Cash insuffisant: {cash:.2f}$ < {required_cash:.2f}$")
            
            validations.append(f"⚠️ Cash limité: Réduit position {position_size} → {max_affordable_qty}")
            position_size = max_affordable_qty
        
        # 1b. Exposition Max par Actif (Risk Concentration)
        if portfolio_value > 0:
            projected_exposure = entry_price * position_size
            max_allowed_exposure = portfolio_value * MAX_POS_EXPOSURE_PCT
            
            if projected_exposure > max_allowed_exposure:
                max_qty_risk = int(max_allowed_exposure / entry_price)
                if max_qty_risk < position_size:
                    validations.append(f"⚠️ Exposition Max ({MAX_POS_EXPOSURE_PCT*100}%): Réduit {position_size} → {max_qty_risk}")
                    position_size = max_qty_risk

        # 1c. Valeur position minimale (Anti-Poussière)
        position_value = entry_price * position_size
        if position_value < MIN_POSITION_VALUE:
            # Exception : Si c'est un penny stock à moins de 1$, on accepte si qty > 10
            if not (entry_price < 1.0 and position_size > 10):
                return _reject(f"Position trop petite: {position_value:.2f}$ < {MIN_POSITION_VALUE}$")
        
        # 1d. Limite nombre de positions
        # On vérifie si c'est une nouvelle position
        is_new_position = True
        for pos in positions:
            if pos['symbol'] == symbol:
                is_new_position = False
                break
                
        if is_new_position and open_positions >= MAX_POSITION_COUNT:
            return _reject(f"Portfolio saturé: {open_positions}/{MAX_POSITION_COUNT} positions")

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
            # Nettoyage des symboles pour match (ex: BTC/USD vs BTC)
            pos_sym = pos['symbol'].replace("/", "").replace("-USD", "")
            target_sym = symbol.replace("/", "").replace("-USD", "")
            
            if pos_sym == target_sym:
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
