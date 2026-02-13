"""
Portfolio Analyzer Agent - SECURISED
- Fix KeyError quand un actif n'a pas de données de corrélation
- Vérifie l'existence des colonnes avant accès
"""

import logging
from typing import Dict, Any, List
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from ..shared.state import AgentState

logger = logging.getLogger("portfolio_analyzer")

GATEWAY_URL = "http://gateway:8000"

# DB locale: raison d'achat pour chaque position
POSITION_REASONS = {}


def store_position_reason(symbol: str, reason: str, initial_sentiment: float = 0):
    """
    Stocke la raison d'achat pour une position dans la base locale.

    Args:
        symbol (str): Symbole de l'actif.
        reason (str): Raison d'achat.
        initial_sentiment (float): Sentiment initial (par défaut 0).

    Effects:
        - Modifie la variable globale POSITION_REASONS.
        - Log d'information.
    """
    POSITION_REASONS[symbol] = {
        "reason": reason,
        "initial_sentiment": initial_sentiment,
        "entry_date": str(pd.Timestamp.now().date())
    }
    logger.info(f"📍 Raison pour {symbol}: {reason}")


def get_position_reasons(symbol: str) -> Dict[str, Any]:
    """
    Récupère la raison d'achat d'une position depuis la base locale.

    Args:
        symbol (str): Symbole de l'actif.

    Returns:
        Dict[str, Any]: Dictionnaire avec raison, sentiment initial, date d'entrée.
    """
    return POSITION_REASONS.get(symbol, {
        "reason": "unknown",
        "initial_sentiment": 0,
        "entry_date": None
    })


def calculate_correlation_matrix(symbols: List[str], lookback_days: int = 30) -> pd.DataFrame:
    """
    Calcule la matrice de corrélation entre plusieurs actifs.

    Args:
        symbols (List[str]): Liste des symboles à corréler.
        lookback_days (int): Fenêtre de calcul en jours (par défaut 30).

    Returns:
        pd.DataFrame: Matrice de corrélation.

    Effects:
        - Appels yfinance pour chaque symbole.
        - Log d'erreur si le calcul échoue.
    """
    try:
        prices = {}
        
        # Silence Yahoo pour éviter le spam de logs rouges
        logging.getLogger("yfinance").setLevel(logging.CRITICAL)
        
        for symbol in symbols:
            try:
                # Nettoyage intelligent (Similaire au Retriever)
                clean = symbol.upper().replace("/", "").replace("-USD", "")
                if clean.endswith("USD") and len(clean) > 3: clean = clean[:-3]
                
                # Liste de candidats pour Yahoo
                candidates = [symbol, clean, f"{clean}-USD"]
                candidates = list(dict.fromkeys(candidates))
                
                data_found = False
                for cand in candidates:
                    data = yf.download(cand, period=f"{lookback_days}d", progress=False)
                    if not data.empty and 'Close' in data.columns:
                        # Gestion MultiIndex (yfinance récent)
                        if isinstance(data.columns, pd.MultiIndex):
                            prices[symbol] = data['Close'][cand] # Mapping Symbol original -> Data
                        else:
                            prices[symbol] = data['Close']
                        data_found = True
                        break
                
                if not data_found:
                    logger.debug(f"⚠️ Pas de data corrélation pour {symbol}")

            except Exception:
                continue
        
        # Rétablir logs
        logging.getLogger("yfinance").setLevel(logging.WARNING)
        
        if len(prices) < 2:
            return pd.DataFrame() # Pas assez de données pour corréler
        
        # Alignement des dates et calcul
        price_df = pd.DataFrame(prices)
        correlation_matrix = price_df.corr()
        
        return correlation_matrix
    
    except Exception as e:
        logger.error(f"❌ Erreur globale matrice: {e}")
        return pd.DataFrame()


def check_correlation_redundancy(new_symbol: str, current_positions: List[str], threshold: float = 0.8) -> Dict[str, Any]:
    """
    Vérifie si une nouvelle opportunité est trop corrélée avec les positions existantes.

    Args:
        new_symbol (str): Symbole de la nouvelle opportunité.
        current_positions (List[str]): Liste des positions actuelles.
        threshold (float): Seuil de corrélation (par défaut 0.8).

    Returns:
        Dict[str, Any]: Indique redondance, corrélation max, recommandations.
    """
    
    if not current_positions:
        return {
            "is_redundant": False,
            "highest_correlation": 0,
            "correlated_with": [],
            "recommendation": "ADD: Première position ou diversification OK"
        }
    
    symbols = current_positions + [new_symbol]
    
    corr_matrix = calculate_correlation_matrix(symbols)
    
    if corr_matrix.empty:
        return {
            "is_redundant": False,
            "highest_correlation": 0,
            "correlated_with": [],
            "recommendation": "UNKNOWN: Données insuffisantes (Safe Pass)"
        }
    
    # --- FIX CRITIQUE: KEYERROR ---
    # Si le new_symbol n'a pas été trouvé par Yahoo, il n'est pas dans la matrice.
    # On ne peut pas calculer sa corrélation, donc on assume qu'il n'est pas corrélé (Safe Pass).
    if new_symbol not in corr_matrix.columns:
        logger.warning(f"⚠️ {new_symbol} absent de la matrice de corrélation (Data manquante).")
        return {
            "is_redundant": False,
            "highest_correlation": 0,
            "correlated_with": [],
            "recommendation": "ADD: Pas de données historique (Nouvel actif ?)"
        }
    # ------------------------------
    
    # Corrélation de new_symbol vs tous les autres
    new_symbol_correlations = corr_matrix[new_symbol]
    
    high_corr = []
    max_corr = 0
    
    for existing_symbol in current_positions:
        # On vérifie aussi que la position existante est dans la matrice
        if existing_symbol in new_symbol_correlations.index:
            corr_value = new_symbol_correlations.get(existing_symbol, 0)
            
            if abs(corr_value) > threshold:
                high_corr.append({
                    "symbol": existing_symbol,
                    "correlation": corr_value
                })
                max_corr = max(abs(corr_value), max_corr)
    
    is_redundant = len(high_corr) > 0
    
    if is_redundant:
        corr_symbols = ", ".join([c["symbol"] for c in high_corr])
        recommendation = f"REDUNDANT: Trop corrélé avec {corr_symbols}"
    else:
        recommendation = "ADD: Diversification OK"
    
    logger.info(f"  Corrélation {new_symbol}: Max={max_corr:.2f} | Redundant={is_redundant}")
    
    return {
        "is_redundant": is_redundant,
        "highest_correlation": max_corr,
        "correlated_with": high_corr,
        "recommendation": recommendation
    }


def check_sector_exposure(new_symbol: str, current_positions: List[str], max_sector_exposure: float = 0.4) -> Dict[str, Any]:
    """
    Vérifie l'exposition sectorielle d'une nouvelle opportunité par rapport au portefeuille.

    Args:
        new_symbol (str): Symbole de la nouvelle opportunité.
        current_positions (List[str]): Liste des positions actuelles.
        max_sector_exposure (float): Seuil maximal d'exposition (par défaut 0.4).

    Returns:
        Dict[str, Any]: Secteur, exposition, avertissement, etc.
    """
    
    # Mapping simplifié symbole -> secteur (Extensible)
    sector_map = {
        "AAPL": "technology", "MSFT": "technology", "NVDA": "technology", "GOOGL": "technology",
        "AMZN": "consumer", "TSLA": "automotive",
        "BTC": "crypto", "ETH": "crypto", "DOGE": "crypto", "SHIB": "crypto", "SOL": "crypto",
        "JPM": "finance", "GS": "finance",
        "XOM": "energy", "CVX": "energy"
    }
    
    all_symbols = current_positions + [new_symbol]
    sector_counts = {}
    
    for symbol in all_symbols:
        # Heuristique simple: si non listé mais ticker court -> crypto
        clean = symbol.replace("-USD", "").upper()
        default_sec = "crypto" if len(clean) <= 5 and clean not in ["AAPL", "TSLA", "MSFT"] else "other"
        
        sector = sector_map.get(clean, default_sec)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    
    # Secteur du nouveau
    clean_new = new_symbol.replace("-USD", "").upper()
    new_symbol_sector = sector_map.get(clean_new, "crypto" if len(clean_new) <= 5 else "other")
    
    sector_exposure = sector_counts.get(new_symbol_sector, 0) / len(all_symbols)
    
    is_overexposed = sector_exposure > max_sector_exposure
    
    warning = ""
    if is_overexposed:
        warning = f"⚠️ {new_symbol_sector.upper()} serait à {sector_exposure*100:.0f}% (max: {max_sector_exposure*100:.0f}%)"
    
    return {
        "new_symbol_sector": new_symbol_sector,
        "sector_exposure": sector_exposure,
        "is_overexposed": is_overexposed,
        "warning": warning
    }


def validate_reason_still_valid(symbol: str, current_sentiment: float) -> Dict[str, Any]:
    """
    Vérifie si la raison initiale d'achat d'une position est toujours valable.

    Args:
        symbol (str): Symbole de l'actif.
        current_sentiment (float): Score de sentiment actuel.

    Returns:
        Dict[str, Any]: Résultat de la validation, recommandation, etc.
    """
    
    reason_data = get_position_reasons(symbol)
    
    initial_reason = reason_data.get("reason", "unknown")
    initial_sentiment = reason_data.get("initial_sentiment", 0)
    
    # Logique simple: si sentiment a flipé du positif au négatif de façon drastique
    sentiment_reversal = (initial_sentiment > 0 and current_sentiment < -0.3)
    
    if sentiment_reversal:
        recommendation = f"EXIT: Raison d'achat expirée (sentiment initial: +{initial_sentiment:.2f}, actuel: {current_sentiment:.2f})"
        return {
            "reason_valid": False,
            "reason": initial_reason,
            "sentiment_change": current_sentiment - initial_sentiment,
            "recommendation": recommendation
        }
    
    return {
        "reason_valid": True,
        "reason": initial_reason,
        "sentiment_change": current_sentiment - initial_sentiment,
        "recommendation": "HOLD: Raison toujours pertinente"
    }


def analyze_portfolio(state: AgentState) -> Dict[str, Any]:
    """
    Agent principal d'analyse du portefeuille face à une nouvelle opportunité.

    Args:
        state (AgentState): Etat de l'agent, doit contenir 'symbol' et 'sentiment_score'.

    Returns:
        Dict[str, Any]: Résultat de l'analyse (corrélation, secteur, recommandations, etc.).

    Effects:
        - Appels API externes (Gateway, yfinance).
        - Logs d'information et d'avertissement.
    """
    
    new_symbol = state.get('symbol', 'UNKNOWN')
    
    print(f"🎒 [Portfolio Analyzer] Analyse {new_symbol} vs portefeuille...")
    
    # 1. Récupère positions actuelles
    current_positions = []
    try:
        pos_resp = requests.get(f"{GATEWAY_URL}/positions", timeout=2)
        if pos_resp.status_code == 200:
            current_positions = [p['symbol'] for p in pos_resp.json()]
    except:
        pass
    
    # 2. Check corrélation
    correlation_check = check_correlation_redundancy(new_symbol, current_positions, threshold=0.8)
    
    # 3. Check exposition sectorielle
    sector_check = check_sector_exposure(new_symbol, current_positions, max_sector_exposure=0.4)
    
    # 4. Check validité existantes
    reason_validity_existing = {}
    current_sentiment = state.get('sentiment_score', 0)
    
    for pos_symbol in current_positions:
        reason_check = validate_reason_still_valid(pos_symbol, current_sentiment)
        if not reason_check["reason_valid"]:
            reason_validity_existing[pos_symbol] = reason_check
    
    # 5. Synthèse
    can_add = not correlation_check["is_redundant"] and not sector_check["is_overexposed"]
    
    reduce_positions = []
    if reason_validity_existing:
        reduce_positions = [pos for pos, data in reason_validity_existing.items() if not data["reason_valid"]]
    
    return {
        "can_add": can_add,
        "current_positions_count": len(current_positions),
        "current_positions": current_positions,
        "correlation_check": correlation_check,
        "sector_check": sector_check,
        "reduce_positions": reduce_positions,
        "positions_to_exit": list(reason_validity_existing.keys()) if reason_validity_existing else [],
        "recommendation": "ADD" if can_add else "SKIP"
    }
