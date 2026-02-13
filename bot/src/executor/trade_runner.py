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
    Exécute (ou prépare) un ordre en fonction de l'état fourni.

    Cette fonction est le point d'entrée du noeud d'exécution du graphe. Elle
    vérifie les conditions de sécurité (prix valide, approbation du gestionnaire
    de risque) et délègue vers l'exécution d'achat/vente. En cas de `hold` ou
    d'absence d'approbation, aucun ordre n'est envoyé.

    Args:
        state (AgentState): Etat complet contenant au minimum les clés:
            - `symbol` (str): symbole de l'actif.
            - `decision` (str): 'buy'|'sell'|'hold'.
            - `approved` (bool): résultat du validateur de risque.
            - `price` (float): prix utilisé pour les checks de sécurité.

    Returns:
        Dict[str, Any]: Structure indiquant l'issue, exemple:
            {"executed": bool, "order_id": Optional[str], "reason": Optional[str]}

    Effects:
        - Émet des logs de niveau `critical`/`error`/`info` selon le cas.
        - Peut faire un POST vers le service Gateway via `_send_order`.
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
    Calcule la taille de position et envoie un ordre d'achat.

    La taille est déterminée en allouant 5% du cash disponible (`cash` dans
    `state`). Des fallback sont appliqués pour garantir une quantité minimale.

    Args:
        symbol (str): Symbole de l'actif à acheter.
        state (AgentState): Etat contenant au moins `cash`, `strategy` et `price`.

    Returns:
        Dict[str, Any]: Résultat de l'appel `_send_order` indiquant succès ou échec.

    Effects:
        - Peut appeler `_send_order` qui effectue un POST vers `{GATEWAY_URL}/orders`.
        - Émet des logs informatifs et d'erreur en cas de conditions non satisfaites.
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
    """
    Prépare et envoie un ordre de vente en fonction de la quantité ajustée.

    Args:
        symbol (str): Symbole de l'actif à vendre.
        state (AgentState): Etat contenant `adjusted_qty` représentant la quantité à vendre.

    Returns:
        Dict[str, Any]: Résultat de l'opération (mêmes clefs que `_send_order`).

    Effects:
        - En cas de `adjusted_qty` insuffisant, utilise `_order_failed` et logge l'erreur.
        - Envoie un POST vers le Gateway si la quantité est suffisante.
    """

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
    """
    Envoie l'ordre au service Gateway via HTTP POST.

    Args:
        order (Dict): Dictionnaire contenant les paramètres de l'ordre
            (symbol, side, quantity, type, ...).

    Returns:
        Dict: Objet indiquant l'exécution: {"executed": bool, "order_id": Optional[str], "reason": Optional[str]}.

    Effects:
        - Effectue un POST HTTP vers `{GATEWAY_URL}/orders`.
        - Logge l'identifiant de l'ordre en cas de succès, ou l'erreur en cas d'échec.
    """

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
    """
    Helper pour uniformiser la réponse d'échec d'ordre.

    Args:
        reason (str): Raison textuelle du rejet/échec.

    Returns:
        Dict: {"executed": False, "reason": reason}.

    Effects:
        - Émet un log d'erreur contenant la raison.
    """

    logger.error(f"❌ Echec ordre: {reason}")
    return {"executed": False, "reason": reason}
