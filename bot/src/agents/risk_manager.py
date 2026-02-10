"""
Risk Validator Agent V2
- Valide la stratégie proposée AVANT envoi à l'executor
- Filtre agressif AVANT les ordres
- Peut ajuster la position size ou rejeter complètement
"""

import logging
from typing import Dict, Any
import requests
from ..shared.state import AgentState

logger = logging.getLogger("risk_validator")

GATEWAY_URL = "http://gateway:8000"

# Limites de risque configurables
MAX_SINGLE_POSITION_RISK_PCT = 0.02  # 2% du portfolio par position
MAX_DAILY_LOSS_PCT = 0.05  # Stop si -5% en un jour
MIN_POSITION_VALUE = 50  # Minimum $50 pour commencer
MAX_POSITION_COUNT = 10  # Max 10 positions ouvertes


def validate_strategy(state: AgentState) -> Dict[str, Any]:
    """Agent principal: valide stratégie avant exécution."""
    
    symbol = state.get('symbol', 'UNKNOWN')
    strategy = state.get('strategy', {})
    decision = state.get('decision', 'hold')
    
    print(f"🛡️ [Risk Validator] Validation de {symbol}...")
    
    if decision == "hold":
        print("  → HOLD: Pas de validation d'ordre.")
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
        
        entry_price = strategy.get("entry_price", 0)
        position_size = strategy.get("position_size", 0)
        sl_level = strategy.get("sl_level", entry_price * 0.97)
        
        # 1a. Cash suffisant?
        required_cash = entry_price * position_size
        
        if cash < required_cash * 1.1:  # 10% buffer
            # Réduit la position size
            adjusted_size = int((cash * 0.9) / entry_price) if entry_price > 0 else 0
            
            if adjusted_size < 1:
                return _reject(f"Cash insuffisant: {cash:.2f}$ < {required_cash:.2f}$")
            
            validations.append(f"⚠️ Cash limité: Réduit position {position_size} → {adjusted_size}")
            position_size = adjusted_size
        
        # 1b. Risk par position < 2% du portfolio
        if portfolio_value > 0:
            risk_amount = (entry_price - sl_level) * position_size
            risk_pct = risk_amount / portfolio_value
            
            if risk_pct > MAX_SINGLE_POSITION_RISK_PCT:
                # Réduit encore
                max_qty = int((portfolio_value * MAX_SINGLE_POSITION_RISK_PCT) / (entry_price - sl_level)) if (entry_price - sl_level) > 0 else position_size
                
                validations.append(f"⚠️ Risk élevé: {risk_pct*100:.2f}% > {MAX_SINGLE_POSITION_RISK_PCT*100:.2f}%. Réduit {position_size} → {max_qty}")
                position_size = max_qty
        
        # 1c. Valeur position minimale
        position_value = entry_price * position_size
        if position_value < MIN_POSITION_VALUE:
            return _reject(f"Position trop petite: {position_value:.2f}$ < {MIN_POSITION_VALUE}$")
        
        # 1d. Max positions
        if open_positions >= MAX_POSITION_COUNT:
            return _reject(f"Portfolio saturé: {open_positions} positions ouvertes (max: {MAX_POSITION_COUNT})")
        
        # 1e. RSI extrême check (override)
        rsi = state.get('rsi', 50)
        if rsi > 85:
            validations.append(f"⚠️ RSI extrême ({rsi:.0f}) - réduire agressivité")
            position_size = int(position_size * 0.7)
        
        # 1f. Peut-on shortchecker positions existantes?
        existing_position = None
        for pos in positions:
            if pos['symbol'] == symbol:
                existing_position = pos
                break
        
        if existing_position:
            validations.append(f"⚠️ Position existante {symbol}: {existing_position['qty']} @ {existing_position['avg_entry_price']}")
        
        # ✅ BUY APPROVED
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
        
        position_qty = strategy.get("position_size", 0)
        current_price = state.get('price', 0)
        
        # 2a. Position existe-t-elle?
        existing_qty = 0
        for pos in positions:
            if pos['symbol'] == symbol:
                existing_qty = int(pos['qty'])
                break
        
        if existing_qty <= 0:
            return _reject(f"Pas de position à vendre: {symbol}")
        
        # 2b. Valeur minimale à vendre
        sell_value = current_price * existing_qty
        if sell_value < MIN_POSITION_VALUE / 2:  # Plus loose pour sells
            validations.append(f"⚠️ Position très petite: {sell_value:.2f}$ (vendre quand même)")
        
        # ✅ SELL APPROVED
        return {
            "approved": True,
            "decision": "sell",
            "reason": "SELL strategy approuvée",
            "adjusted_qty": existing_qty,
            "cash_available": cash,
            "portfolio_value": portfolio_value,
            "validations": validations,
            "strategy": strategy
        }
    
    # Default
    return {
        "approved": False,
        "decision": "unknown",
        "reason": "Décision invalide",
        "adjusted_qty": 0
    }


def _reject(reason: str) -> Dict[str, Any]:
    """Helper pour rejeter une stratégie."""
    logger.warning(f"🛑 Risk validation REJECT: {reason}")
    return {
        "approved": False,
        "decision": "rejected",
        "reason": f"RISK REJECT: {reason}",
        "adjusted_qty": 0
    }
