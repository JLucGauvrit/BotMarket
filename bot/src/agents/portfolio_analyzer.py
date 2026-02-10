"""
Portfolio Analyzer Agent
- Analyse TOUTES les positions vs nouvelle opportunité
- Détecte corrélation (> 0.8 = redondant)
- Vérifie max exposure par secteur
- Track raison d'achat (si expirée = exit signal)
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
# {symbol: {"reason": "bullish_divergence", "entry_date": "2024-01-15", "initial_sentiment": 0.75}}
POSITION_REASONS = {}


def store_position_reason(symbol: str, reason: str, initial_sentiment: float = 0):
    """Stocke la raison d'achat pour une position."""
    POSITION_REASONS[symbol] = {
        "reason": reason,
        "initial_sentiment": initial_sentiment,
        "entry_date": str(pd.Timestamp.now().date())
    }
    logger.info(f"📍 Raison pour {symbol}: {reason}")


def get_position_reasons(symbol: str) -> Dict[str, Any]:
    """Récupère la raison d'achat d'une position."""
    return POSITION_REASONS.get(symbol, {
        "reason": "unknown",
        "initial_sentiment": 0,
        "entry_date": None
    })


def calculate_correlation_matrix(symbols: List[str], lookback_days: int = 30) -> pd.DataFrame:
    """Calcule matrice de corrélation entre symboles."""
    
    try:
        prices = {}
        
        for symbol in symbols:
            try:
                # Nettoyage du symbole pour Yahoo
                yahoo_symbol = symbol.replace("SHIB", "SHIB-USD").replace("DOGE", "DOGE-USD")
                if "-" not in yahoo_symbol:
                    yahoo_symbol = f"{yahoo_symbol}-USD"
                
                data = yf.download(yahoo_symbol, period=f"{lookback_days}d", progress=False)
                
                if not data.empty:
                    prices[symbol] = data['Close']
            
            except Exception as e:
                logger.warning(f"⚠️ Pas de données pour {symbol}: {e}")
        
        if len(prices) < 2:
            logger.warning("Pas assez de symboles pour calculer corrélation")
            return pd.DataFrame()
        
        # DataFrame prix
        price_df = pd.DataFrame(prices)
        
        # Corrélation
        correlation_matrix = price_df.corr()
        
        logger.info(f"✅ Matrice corrélation calculée ({len(symbols)} symboles)")
        
        return correlation_matrix
    
    except Exception as e:
        logger.error(f"❌ Erreur matrice corrélation: {e}")
        return pd.DataFrame()


def check_correlation_redundancy(new_symbol: str, current_positions: List[str], threshold: float = 0.8) -> Dict[str, Any]:
    """
    Vérifie si nouvelle opportunité est trop corrélée avec positions existantes.
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
            "recommendation": "UNKNOWN: Données insuffisantes, NEUTRAL PASS"
        }
    
    # Corrélation de new_symbol vs tous les autres
    new_symbol_correlations = corr_matrix[new_symbol]
    
    high_corr = []
    max_corr = 0
    
    for existing_symbol in current_positions:
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
    Vérifie l'exposition sectorielle.
    Exemple: Tech ne doit pas dépasser 40% du portefeuille.
    """
    
    # Mapping simplifié symbole -> secteur
    sector_map = {
        "AAPL": "technology", "MSFT": "technology", "NVDA": "technology", "GOOGL": "technology",
        "AMZN": "consumer", "TSLA": "automotive",
        "BTC": "crypto", "ETH": "crypto", "DOGE": "crypto", "SHIB": "crypto",
        "JPM": "finance", "GS": "finance",
        "XOM": "energy", "CVX": "energy"
    }
    
    all_symbols = current_positions + [new_symbol]
    sector_counts = {}
    
    for symbol in all_symbols:
        sector = sector_map.get(symbol.upper(), "other")
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    
    new_symbol_sector = sector_map.get(new_symbol.upper(), "other")
    sector_exposure = sector_counts.get(new_symbol_sector, 0) / len(all_symbols)
    
    is_overexposed = sector_exposure > max_sector_exposure
    
    warning = ""
    if is_overexposed:
        warning = f"⚠️ {new_symbol_sector.upper()} serait à {sector_exposure*100:.0f}% (max: {max_sector_exposure*100:.0f}%)"
    
    logger.info(f"  Exposition {new_symbol_sector}: {sector_exposure*100:.0f}% | Overexposed: {is_overexposed}")
    
    return {
        "new_symbol_sector": new_symbol_sector,
        "sector_exposure": sector_exposure,
        "is_overexposed": is_overexposed,
        "warning": warning
    }


def validate_reason_still_valid(symbol: str, current_sentiment: float) -> Dict[str, Any]:
    """
    Vérifie si la raison initiale d'achat est toujours valable.
    Exemple: si on a acheté sur "sentiment bullish (0.7)" mais sentiment est maintenant -0.5
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
    """Agent principal: analyse portefeuille vs nouvelle opportunité."""
    
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
    
    logger.info(f"  Positions actuelles: {current_positions}")
    
    # 2. Check corrélation
    correlation_check = check_correlation_redundancy(new_symbol, current_positions, threshold=0.8)
    
    # 3. Check exposition sectorielle
    sector_check = check_sector_exposure(new_symbol, current_positions, max_sector_exposure=0.4)
    
    # 4. Check si raison d'achat toujours valide (pour positions existantes)
    # Ce check n'affecte pas la NOUVELLE opportunité, mais signale des positions à exit
    reason_validity_existing = {}
    current_sentiment = state.get('sentiment_score', 0)
    
    for pos_symbol in current_positions:
        reason_check = validate_reason_still_valid(pos_symbol, current_sentiment)
        if not reason_check["reason_valid"]:
            reason_validity_existing[pos_symbol] = reason_check
    
    # 5. Synthèse
    can_add = not correlation_check["is_redundant"] and not sector_check["is_overexposed"]
    
    # Positions à réduire ou fermer
    reduce_positions = []
    if reason_validity_existing:
        reduce_positions = [pos for pos, data in reason_validity_existing.items() if not data["reason_valid"]]
    
    result = {
        "can_add": can_add,
        "current_positions_count": len(current_positions),
        "current_positions": current_positions,
        "correlation_check": correlation_check,
        "sector_check": sector_check,
        "reduce_positions": reduce_positions,
        "positions_to_exit": list(reason_validity_existing.keys()) if reason_validity_existing else [],
        "recommendation": _synthesize_portfolio_recommendation(
            can_add, correlation_check, sector_check, reduce_positions
        )
    }
    
    print(f"  Can add {new_symbol}: {can_add} | Reduce: {len(reduce_positions)} | Exit: {len(reason_validity_existing)}")
    
    return result


def _synthesize_portfolio_recommendation(can_add: bool, corr_check: Dict, sector_check: Dict, reduce_positions: List) -> str:
    """Synthèse en recommandation unique."""
    
    if reduce_positions:
        return f"CLOSE_first: {', '.join(reduce_positions[:2])} (raison expirée)"
    
    if not can_add:
        if corr_check["is_redundant"]:
            return f"SKIP: Trop corrélé avec {corr_check['correlated_with'][0]['symbol']}"
        elif sector_check["is_overexposed"]:
            return f"SKIP: {sector_check['warning']}"
    
    return "ADD: Opportunité saine"
