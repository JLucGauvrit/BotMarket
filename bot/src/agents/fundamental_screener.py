"""
Fundamental Screener Agent
- Pull P/E, PEG, Debt/Equity, Revenue Growth
- Détecte trappes (pump & dump, overvalued)
- Retourne Pass/Fail + métriques
"""

import yfinance as yf
import requests
import logging
from typing import Dict, Any
from ..shared.state import AgentState

logger = logging.getLogger("fundamental_screener")

# Utilise Alpha Vantage API (gratuit: 5 calls/min, 500/day)
ALPHA_VANTAGE_KEY = "demo"  # À remplacer par vraie clé


def get_stock_fundamentals(symbol: str) -> Dict[str, Any]:
    """
    Récupère les données fondamentales d'une action via yfinance.

    Args:
        symbol (str): Symbole de l'action (ex: 'AAPL').

    Returns:
        Dict[str, Any]: Dictionnaire des métriques fondamentales (P/E, PEG, etc.).

    Effects:
        - Appelle l'API Yahoo Finance via yfinance.
        - Log d'information ou d'erreur selon le résultat.
    """
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Extraction des métriques clés
        pe_ratio = info.get("trailingPE", None)
        peg_ratio = info.get("pegRatio", None)
        debt_to_equity = info.get("debtToEquity", None)
        revenue_growth = info.get("revenuePerShare", None)
        eps_growth_this_year = info.get("epsTrailingTwelveMonths", None)
        dividend_yield = info.get("dividendYield", 0)
        market_cap = info.get("marketCap", 0)
        
        # Calcul du ratio P/B
        price_to_book = info.get("priceToBook", None)
        
        # État de santé
        current_ratio = info.get("currentRatio", None)  # Liquidité
        profit_margin = info.get("profitMargins", None)
        
        fundamentals = {
            "pe_ratio": pe_ratio,
            "peg_ratio": peg_ratio,
            "debt_to_equity": debt_to_equity,
            "price_to_book": price_to_book,
            "dividend_yield": dividend_yield,
            "current_ratio": current_ratio,
            "profit_margin": profit_margin,
            "market_cap": market_cap,
            "symbol_type": "stock"
        }
        
        logger.info(f"✅ Fondamentaux {symbol}: P/E={pe_ratio}, Div={dividend_yield}")
        return fundamentals
    
    except Exception as e:
        logger.error(f"❌ Erreur fondamentaux {symbol}: {e}")
        return {}


def get_crypto_fundamentals(symbol: str) -> Dict[str, Any]:
    """
    Récupère les données fondamentales d'une crypto via l'API CoinGecko.

    Args:
        symbol (str): Symbole de la crypto (ex: 'BTC').

    Returns:
        Dict[str, Any]: Dictionnaire des métriques fondamentales (market cap, supply, etc.).

    Effects:
        - Appelle l'API CoinGecko.
        - Log d'information ou d'erreur selon le résultat.
    """
    
    try:
        # Mapping symbole -> CoinGecko ID
        symbol_to_id = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "DOGE": "dogecoin",
            "SHIB": "shiba-inu",
            "USDC": "usd-coin"
        }
        
        coin_id = symbol_to_id.get(symbol.upper())
        
        if not coin_id:
            logger.warning(f"⚠️ Crypto inconnue: {symbol}")
            return {}
        
        # CoinGecko API (gratuit, pas d'auth)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        
        data = resp.json()
        
        # Extraction
        market_data = data.get("market_data", {})
        
        fundamentals = {
            "market_cap": market_data.get("market_cap", {}).get("usd", 0),
            "market_cap_rank": data.get("market_cap_rank"),
            "total_volume_24h": market_data.get("total_volume", {}).get("usd", 0),
            "circulating_supply": market_data.get("circulating_supply", 0),
            "max_supply": market_data.get("max_supply", 0),
            "price_change_24h": market_data.get("price_change_percentage_24h", 0),
            "price_change_7d": market_data.get("price_change_percentage_7d", 0),
            "price_change_30d": market_data.get("price_change_percentage_30d", 0),
            "market_cap_change_24h": market_data.get("market_cap_change_percentage_24h_usd", 0),
            "symbol_type": "crypto"
        }
        
        logger.info(f"✅ Crypto fundamentals {symbol}: Market Cap Rank={fundamentals['market_cap_rank']}")
        return fundamentals
    
    except Exception as e:
        logger.error(f"❌ Erreur crypto fundamentals {symbol}: {e}")
        return {}


def screen_stock(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applique la logique de screening sur les fondamentaux d'une action.

    Args:
        fundamentals (Dict[str, Any]): Dictionnaire des métriques fondamentales.

    Returns:
        Dict[str, Any]: Résultat du screening (pass, score, issues, warnings, reason).
    """
    
    pe = fundamentals.get("pe_ratio")
    peg = fundamentals.get("peg_ratio")
    debt_to_equity = fundamentals.get("debt_to_equity")
    current_ratio = fundamentals.get("current_ratio")
    
    issues = []
    warnings = []
    scores = []
    
    # 1. P/E trop élevé (> 50 ET croissance faible)
    if pe and pe > 50:
        if peg and peg < 1:  # Mais PEG bon
            warnings.append(f"P/E élevé ({pe:.1f}) mais PEG acceptable ({peg:.1f})")
            scores.append(0.6)
        else:
            issues.append(f"OVERVALUED: P/E={pe:.1f} (normal: 15-25)")
            scores.append(0.2)
    elif pe and pe > 25:
        warnings.append(f"P/E modérément élevé ({pe:.1f})")
        scores.append(0.7)
    elif pe and pe > 0:
        scores.append(0.9)
    
    # 2. Liquidité (current ratio < 1.0 = risque)
    if current_ratio and current_ratio < 1.0:
        issues.append(f"Liquidité faible: Current Ratio={current_ratio:.2f}")
        scores.append(0.3)
    elif current_ratio and current_ratio >= 1.5:
        scores.append(0.95)
    
    # 3. Endettement
    if debt_to_equity and debt_to_equity > 2.0:
        warnings.append(f"Endettement élevé: D/E={debt_to_equity:.2f}")
        scores.append(0.5)
    elif debt_to_equity and debt_to_equity > 0:
        scores.append(0.85)
    
    # Synthèse
    pass_fail = len(issues) == 0
    final_score = sum(scores) / len(scores) if scores else 0.5
    
    return {
        "pass": pass_fail,
        "score": final_score,
        "issues": issues,
        "warnings": warnings,
        "reason": "PASS" if pass_fail else f"FAIL: {'; '.join(issues)}"
    }


def screen_crypto(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applique la logique de screening sur les fondamentaux d'une crypto.

    Args:
        fundamentals (Dict[str, Any]): Dictionnaire des métriques fondamentales.

    Returns:
        Dict[str, Any]: Résultat du screening (pass, score, issues, warnings, reason).
    """
    
    market_cap_rank = fundamentals.get("market_cap_rank", 1000)
    mc_change_24h = fundamentals.get("market_cap_change_24h", 0)
    price_change_24h = fundamentals.get("price_change_24h", 0)
    max_supply = fundamentals.get("max_supply")
    
    issues = []
    warnings = []
    scores = []
    
    # 1. Pump & dump détection: +300% en 24h
    if price_change_24h > 300:
        issues.append(f"PUMP DETECTED: +{price_change_24h:.0f}% en 24h (risque crash)")
        scores.append(0.2)
    elif price_change_24h > 100:
        warnings.append(f"Mouvement violent: +{price_change_24h:.0f}% en 24h")
        scores.append(0.5)
    elif price_change_24h > 20:
        warnings.append(f"Volatilité: +{price_change_24h:.0f}% en 24h")
        scores.append(0.7)
    elif abs(price_change_24h) < 10:
        scores.append(0.85)
    
    # 2. Market cap rank (plus bas = plus établi)
    if market_cap_rank and market_cap_rank > 500:
        issues.append(f"Très faible cap rank (#{market_cap_rank}), risque liquidity")
        scores.append(0.3)
    elif market_cap_rank and market_cap_rank < 100:
        scores.append(0.9)
    
    # 3. Supply inflation (max_supply > circulating x 10)
    if max_supply and max_supply > 0:
        circ_supply = fundamentals.get("circulating_supply", max_supply)
        if max_supply > circ_supply * 10:
            warnings.append(f"Supply inflation risk: max={max_supply} vs circulating={circ_supply}")
            scores.append(0.6)
        else:
            scores.append(0.85)
    
    pass_fail = len(issues) == 0
    final_score = sum(scores) / len(scores) if scores else 0.5
    
    return {
        "pass": pass_fail,
        "score": final_score,
        "issues": issues,
        "warnings": warnings,
        "reason": "PASS" if pass_fail else f"FAIL: {'; '.join(issues)}"
    }


def screen_fundamentals(state: AgentState) -> Dict[str, Any]:
    """
    Agent principal de screening des fondamentaux (actions ou cryptos).

    Args:
        state (AgentState): Etat de l'agent, doit contenir 'symbol'.

    Returns:
        Dict[str, Any]: Résultat du screening, enrichi des fondamentaux collectés.

    Effects:
        - Appels API externes (Yahoo, CoinGecko).
        - Logs d'information et d'avertissement.
    """
    
    symbol = state.get('symbol', 'UNKNOWN')
    print(f"📊 [Fundamental Screener] Analyse {symbol}...")
    
    # 1. Détermine le type (action vs crypto)
    is_crypto = symbol.upper() in ["BTC", "ETH", "DOGE", "SHIB", "ADA", "XRP", "USDC"]
    
    # 2. Collecte les données
    if is_crypto:
        fundamentals = get_crypto_fundamentals(symbol)
        if not fundamentals:
            # Fallback: retour neutre
            return {
                "pass": True,  # Laisse passer
                "score": 0.7,
                "issues": [],
                "warnings": ["Données fondamentales indisponibles"],
                "reason": "Data unavailable - NEUTRAL PASS",
                "symbol_type": "crypto"
            }
        screening = screen_crypto(fundamentals)
    else:
        fundamentals = get_stock_fundamentals(symbol)
        if not fundamentals:
            return {
                "pass": True,
                "score": 0.7,
                "issues": [],
                "warnings": ["Données fondamentales indisponibles"],
                "reason": "Data unavailable - NEUTRAL PASS",
                "symbol_type": "stock"
            }
        screening = screen_stock(fundamentals)
    
    # 3. Synthèse
    result = {
        **screening,
        "fundamentals": fundamentals,
        "symbol_type": "crypto" if is_crypto else "stock"
    }
    
    print(f"  Score: {screening['score']:.2f} | Pass: {screening['pass']} | {screening['reason'][:50]}")
    
    return result
