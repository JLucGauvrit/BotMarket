"""
Market Regime Detector Agent
- Détermine le contexte global (bull, bear, greed, fear)
- Ajuste risk multiplier en conséquence
- Flag si corrélation BTC-stocks haute = risk-off
"""

import yfinance as yf
import requests
import logging
from typing import Dict, Any, Optional
from ..shared.state import AgentState
import numpy as np

logger = logging.getLogger("market_regime")


def get_fear_and_greed_index() -> Dict[str, Any]:
    """
    Récupère le Fear & Greed Index depuis l'API alternative.me.

    Returns:
        Dict[str, Any]: Valeur, classification et disponibilité de l'index.

    Effects:
        - Appel HTTP GET vers l'API externe.
        - Log d'information ou d'erreur.
    """
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        
        data = resp.json()
        
        if data.get("data"):
            index_data = data["data"][0]
            value = int(index_data.get("value", 50))
            classification = index_data.get("value_classification", "Neutral")
            
            logger.info(f"✅ Fear & Greed Index: {value} ({classification})")
            
            return {
                "value": value,
                "classification": classification,
                "available": True
            }
        
        return {"value": 50, "classification": "Neutral", "available": False}
    
    except Exception as e:
        logger.error(f"❌ Erreur Fear & Greed: {e}")
        return {"value": 50, "classification": "Neutral", "available": False}


def get_volatility_index() -> Dict[str, float]:
    """
    Récupère l'indice de volatilité VIX via Yahoo Finance.

    Returns:
        Dict[str, float]: Valeur du VIX, moyenne 30j, disponibilité.

    Effects:
        - Appel yfinance.
        - Log d'information ou d'erreur.
    """
    try:
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period="1d")
        
        if vix_data.empty:
            return {"vix": 20.0, "available": False}
        
        current_vix = float(vix_data['Close'].iloc[-1])
        
        # Calcul de la moyenne 30j
        vix_30d = vix.history(period="1mo")
        avg_vix_30d = float(vix_30d['Close'].mean())
        
        logger.info(f"✅ VIX: {current_vix:.2f} (30d avg: {avg_vix_30d:.2f})")
        
        return {
            "vix": current_vix,
            "vix_30d_avg": avg_vix_30d,
            "available": True
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur VIX: {e}")
        return {"vix": 20.0, "vix_30d_avg": 20.0, "available": False}


def get_btc_trend(period: str = "1mo") -> Dict[str, Any]:
    """
    Détermine la tendance de BTC sur une période donnée.

    Args:
        period (str): Période d'analyse (ex: '1mo').

    Returns:
        Dict[str, Any]: Tendance, variation en %, prix courant, disponibilité.

    Effects:
        - Appel yfinance.
        - Log d'information ou d'erreur.
    """
    try:
        btc = yf.Ticker("BTC-USD")
        btc_data = btc.history(period=period)
        
        if btc_data.empty:
            return {"trend": "unknown", "change_pct": 0}
        
        first_price = float(btc_data['Close'].iloc[0])
        last_price = float(btc_data['Close'].iloc[-1])
        
        change_pct = ((last_price - first_price) / first_price) * 100
        
        if change_pct > 10:
            trend = "strong_bullish"
        elif change_pct > 0:
            trend = "bullish"
        elif change_pct > -10:
            trend = "bearish"
        else:
            trend = "strong_bearish"
        
        logger.info(f"✅ BTC {period}: {change_pct:+.2f}% ({trend})")
        
        return {
            "trend": trend,
            "change_pct": change_pct,
            "current_price": last_price,
            "available": True
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur BTC trend: {e}")
        return {"trend": "unknown", "change_pct": 0, "available": False}


def get_correlation_btc_stocks(lookback_days: int = 30) -> Dict[str, float]:
    """
    Calcule la corrélation entre BTC et SPY sur une période donnée.

    Args:
        lookback_days (int): Fenêtre de calcul en jours.

    Returns:
        Dict[str, float]: Corrélation et disponibilité.

    Effects:
        - Appel yfinance.
        - Log d'information ou d'erreur.
    """
    try:
        # BTC-USD historique
        btc = yf.Ticker("BTC-USD")
        btc_data = btc.history(period=f"{lookback_days}d")
        
        # SPY historique (S&P 500 proxy)
        spy = yf.Ticker("SPY")
        spy_data = spy.history(period=f"{lookback_days}d")
        
        if btc_data.empty or spy_data.empty:
            return {"correlation": 0.5, "available": False}
        
        # Alignment dates
        common_dates = btc_data.index.intersection(spy_data.index)
        
        if len(common_dates) < 5:
            return {"correlation": 0.5, "available": False}
        
        btc_returns = btc_data.loc[common_dates, 'Close'].pct_change().dropna()
        spy_returns = spy_data.loc[common_dates, 'Close'].pct_change().dropna()
        
        # Pearson correlation
        correlation = btc_returns.corr(spy_returns)
        
        logger.info(f"✅ BTC-SPY Correlation ({lookback_days}d): {correlation:.3f}")
        
        return {
            "correlation": float(correlation),
            "available": True
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur corrélation BTC-SPY: {e}")
        return {"correlation": 0.5, "available": False}


def detect_market_regime(
    vix: float,
    fear_greed: int,
    btc_trend: str,
    correlation: float
) -> Dict[str, Any]:
    """
    Détermine le régime de marché global à partir de plusieurs indicateurs.

    Args:
        vix (float): Valeur du VIX.
        fear_greed (int): Score Fear & Greed.
        btc_trend (str): Tendance BTC ('bullish', 'bearish', etc.).
        correlation (float): Corrélation BTC-SPY.

    Returns:
        Dict[str, Any]: Régime, multiplicateur de position, reasoning, recommandation d'action.
    """
    
    regime = "unknown"
    position_multiplier = 1.0
    reasoning = []
    
    # Analyse VIX
    vix_signal = "neutral"
    if vix > 30:
        vix_signal = "fear"
        position_multiplier *= 0.6  # Réduis agressivité
        reasoning.append(f"VIX élevé ({vix:.1f}) = PEUR de marché")
    elif vix < 15:
        vix_signal = "complacency"
        position_multiplier *= 1.1
        reasoning.append(f"VIX bas ({vix:.1f}) = faible volatilité")
    
    # Analyse Fear & Greed
    greed_signal = "neutral"
    if fear_greed > 80:
        greed_signal = "extreme_greed"
        position_multiplier *= 0.7  # Prendre profits
        reasoning.append(f"Extrême GREED ({fear_greed}) = sell signals")
    elif fear_greed < 30:
        greed_signal = "extreme_fear"
        position_multiplier *= 1.2  # Buying opportunity
        reasoning.append(f"Extrême PEUR ({fear_greed}) = buying opportunity")
    
    # BTC Trend
    if "strong_" in btc_trend:
        if "bullish" in btc_trend:
            position_multiplier *= 1.1
            reasoning.append("BTC fort haussier = risk-on")
        else:
            position_multiplier *= 0.7
            reasoning.append("BTC fort baissier = risk-off")
    
    # Corrélation BTC-Stocks
    if correlation > 0.7:
        reasoning.append(f"Corrélation BTC-SPY forte ({correlation:.2f}) = Risk-on dominant")
        regime = "risk_on_correlated"
    elif correlation < 0.3:
        reasoning.append(f"Corrélation BTC-SPY faible ({correlation:.2f}) = Diversification OK")
        regime = "diversified"
    else:
        regime = "partially_correlated"
    
    # Synthèse finale
    if position_multiplier < 0.7:
        final_regime = "risk_off"
    elif position_multiplier > 1.2:
        final_regime = "risk_on"
    else:
        final_regime = regime if regime != "unknown" else "neutral"
    
    # Cap à [0.3, 1.5]
    position_multiplier = max(0.3, min(1.5, position_multiplier))
    
    return {
        "regime": final_regime,
        "position_multiplier": position_multiplier,
        "vix": vix,
        "fear_greed": fear_greed,
        "btc_trend": btc_trend,
        "btc_stocks_correlation": correlation,
        "reasoning": reasoning,
        "action_recommendation": _get_action_from_regime(final_regime, position_multiplier)
    }


def _get_action_from_regime(regime: str, multiplier: float) -> str:
    """
    Génère une recommandation d'action en fonction du régime de marché.

    Args:
        regime (str): Régime détecté ('risk_on', 'risk_off', etc.).
        multiplier (float): Multiplicateur de position.

    Returns:
        str: Recommandation d'action ('CLOSE_POSITIONS_or_GO_SHORT', etc.).
    """
    
    if regime == "risk_off":
        if multiplier < 0.5:
            return "CLOSE_POSITIONS_or_GO_SHORT"
        else:
            return "REDUCE_POSITION_SIZES"
    elif regime == "risk_on":
        if multiplier > 1.2:
            return "SCALE_IN_on_dips"
        else:
            return "NORMAL_BUY_SIGNALS"
    else:
        return "WAIT_for_clarity"


def detect_market_regime_agent(state: Optional[AgentState] = None) -> Dict[str, Any]:
    """
    Agent principal d'analyse du contexte global de marché.

    Args:
        state (AgentState, optionnel): Etat de l'agent (non utilisé ici).

    Returns:
        Dict[str, Any]: Résultat de l'analyse de régime (régime, multiplicateur, reasoning, etc.).

    Effects:
        - Appels API externes (yfinance, alternative.me).
        - Logs d'information et d'erreur.
    """
    
    print("🌍 [Market Regime] Analyse du contexte global...")
    
    # 1. Collecte données
    vix_data = get_volatility_index()
    fear_greed_data = get_fear_and_greed_index()
    btc_trend_data = get_btc_trend(period="1mo")
    correlation_data = get_correlation_btc_stocks(lookback_days=30)
    
    # 2. Détection du régime
    regime = detect_market_regime(
        vix=vix_data.get("vix", 20),
        fear_greed=fear_greed_data.get("value", 50),
        btc_trend=btc_trend_data.get("trend", "unknown"),
        correlation=correlation_data.get("correlation", 0.5)
    )
    
    result = {
        **regime,
        "data_availability": {
            "vix": vix_data.get("available", False),
            "fear_greed": fear_greed_data.get("available", False),
            "btc_trend": btc_trend_data.get("available", False),
            "correlation": correlation_data.get("available", False)
        }
    }
    
    print(f"  Régime: {regime['regime']} | Multiplier: {regime['position_multiplier']:.2f}x | Rec: {regime['action_recommendation']}")
    
    return result
