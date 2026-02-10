"""
TECHNICAL ANALYZER V3 - FIXED PANDAS ISSUES
Fix tous les bugs: RSI format, MACD Series, Bollinger ambiguous, S/R DataFrame
Production-ready avec gestion erreurs robuste.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ============ TECHNICAL ANALYSIS - FIXED ============

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    Calcule RSI correctement sans erreurs pandas.
    
    Args:
        prices: Series de prix (Close)
        period: Période RSI (défaut 14)
    
    Returns:
        float RSI entre 0-100
    """
    if len(prices) < period + 1:
        return 50.0  # Neutre si pas assez de données
    
    try:
        # Différences entre closes consécutifs
        deltas = prices.diff()
        
        # Séparer gains et pertes
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)
        
        # Average Gain/Loss (Wilder's method)
        avg_gain = gains.rolling(window=period).mean()
        avg_loss = losses.rolling(window=period).mean()
        
        # RS et RSI
        rs = avg_gain / (avg_loss + 1e-10)  # Évite division par zéro
        rsi = 100 - (100 / (1 + rs))
        
        # Retourner dernière valeur (IMPORTANT: .item() pour éviter FutureWarning)
        rsi_value = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
        
        logger.debug(f"✅ RSI calculé: {rsi_value:.2f}")
        return rsi_value
        
    except Exception as e:
        logger.error(f"❌ Erreur RSI: {e}")
        return 50.0


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    Calcule MACD correctement sans erreurs Series.
    
    Returns:
        dict avec macd, signal, histogram, status
    """
    if len(prices) < slow + signal:
        return {
            "macd": 0.0,
            "signal": 0.0,
            "histogram": 0.0,
            "status": "insufficient_data"
        }
    
    try:
        # EMA
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        # Histogram
        histogram = macd_line - signal_line
        
        # ✅ IMPORTANT: Utiliser .iloc[-1] puis .item() pour éviter FutureWarning
        macd_val = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0.0
        signal_val = float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else 0.0
        hist_val = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0
        
        # Déterminer statut
        prev_hist = float(histogram.iloc[-2]) if len(histogram) > 1 else 0.0
        
        if hist_val > 0 and prev_hist <= 0:
            status = "bullish_crossover"
        elif hist_val < 0 and prev_hist >= 0:
            status = "bearish_crossover"
        elif hist_val > 0:
            status = "bullish_momentum"
        elif hist_val < 0:
            status = "bearish_momentum"
        else:
            status = "neutral"
        
        logger.debug(f"✅ MACD calculé: {macd_val:.4f} | Signal: {signal_val:.4f} | Status: {status}")
        
        return {
            "macd": macd_val,
            "signal": signal_val,
            "histogram": hist_val,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur MACD: {e}")
        return {
            "macd": 0.0,
            "signal": 0.0,
            "histogram": 0.0,
            "status": "error"
        }


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> dict:
    """
    Calcule Bollinger Bands correctement (fix pour ambiguous truth value).
    
    Returns:
        dict avec upper, middle, lower, position
    """
    if len(prices) < period:
        return {
            "upper": 0.0,
            "middle": 0.0,
            "lower": 0.0,
            "position": "insufficient_data"
        }
    
    try:
        # SMA et écart-type
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        # Bandes
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        # ✅ IMPORTANT: Utiliser .iloc[-1] puis float() pour la dernière valeur
        current_price = float(prices.iloc[-1])
        upper_val = float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else current_price
        lower_val = float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else current_price
        middle_val = float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else current_price
        
        # Déterminer position (FIX: utiliser float comparison, pas Series comparison)
        if current_price <= lower_val + (upper_val - lower_val) * 0.1:
            position = "at_lower_band"
        elif current_price >= upper_val - (upper_val - lower_val) * 0.1:
            position = "at_upper_band"
        elif current_price <= middle_val:
            position = "below_middle"
        else:
            position = "above_middle"
        
        logger.debug(f"✅ Bollinger calculé: Upper={upper_val:.2f} | Mid={middle_val:.2f} | Lower={lower_val:.2f} | Position={position}")
        
        return {
            "upper": upper_val,
            "middle": middle_val,
            "lower": lower_val,
            "position": position
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur Bollinger: {e}")
        current_price = float(prices.iloc[-1]) if len(prices) > 0 else 0.0
        return {
            "upper": current_price * 1.05,
            "middle": current_price,
            "lower": current_price * 0.95,
            "position": "error"
        }


def calculate_support_resistance(prices: pd.Series, window: int = 20) -> dict:
    """
    Calcule Support/Resistance (fix pour DataFrame.between error).
    
    Returns:
        dict avec support, resistance, levels
    """
    if len(prices) < window * 2:
        current = float(prices.iloc[-1])
        return {
            "support": current * 0.95,
            "resistance": current * 1.05,
            "levels": []
        }
    
    try:
        # Rolling min/max (sur DataFrame, pas Series)
        rolling_min = prices.rolling(window=window).min()
        rolling_max = prices.rolling(window=window).max()
        
        # ✅ IMPORTANT: Convertir en float pour éviter ambiguous truth value
        support_val = float(rolling_min.iloc[-1]) if not pd.isna(rolling_min.iloc[-1]) else float(prices.iloc[-1])
        resistance_val = float(rolling_max.iloc[-1]) if not pd.isna(rolling_max.iloc[-1]) else float(prices.iloc[-1])
        
        current_price = float(prices.iloc[-1])
        
        # Générer niveaux
        levels = []
        if support_val != resistance_val:
            step = (resistance_val - support_val) / 3
            for i in range(1, 3):
                level = support_val + (step * i)
                levels.append({
                    "level": level,
                    "type": "resistance" if level > current_price else "support"
                })
        
        logger.debug(f"✅ S/R calculé: Support={support_val:.2f} | Resistance={resistance_val:.2f}")
        
        return {
            "support": support_val,
            "resistance": resistance_val,
            "levels": levels
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur S/R: {e}")
        current = float(prices.iloc[-1]) if len(prices) > 0 else 100.0
        return {
            "support": current * 0.95,
            "resistance": current * 1.05,
            "levels": []
        }


def determine_trend(prices: pd.Series, period: int = 50) -> str:
    """
    Détermine tendance (FIX pour ambiguous Series comparison).
    
    Returns:
        "bullish", "bearish", or "sideways"
    """
    if len(prices) < period:
        return "unknown"
    
    try:
        # SMA simple
        sma_short = prices.rolling(window=20).mean()
        sma_long = prices.rolling(window=period).mean()
        
        # ✅ IMPORTANT: Comparaison de floats, pas Series
        current_price = float(prices.iloc[-1])
        sma_short_val = float(sma_short.iloc[-1]) if not pd.isna(sma_short.iloc[-1]) else current_price
        sma_long_val = float(sma_long.iloc[-1]) if not pd.isna(sma_long.iloc[-1]) else current_price
        
        # Logique trend (float to float comparison!)
        if sma_short_val > sma_long_val and current_price > sma_short_val:
            trend = "bullish"
        elif sma_short_val < sma_long_val and current_price < sma_short_val:
            trend = "bearish"
        else:
            trend = "sideways"
        
        logger.debug(f"✅ Trend déterminé: {trend}")
        return trend
        
    except Exception as e:
        logger.error(f"❌ Erreur trend: {e}")
        return "unknown"


# ============ AGENT ANALYZER ============

def analyze_technical(state: dict) -> dict:
    """
    Agent Technical Analyzer FIXED - compile toutes les analyses.
    
    Retourne:
        dict avec rsi, macd, bollinger, trend, support, resistance, signal
    """
    
    symbol = state.get("symbol", "UNKNOWN")
    prices_data = state.get("prices_df", None)
    
    logger.info(f"📈 [Technical Analyzer] Analyse de {symbol}...")
    
    # Default fallback
    default_response = {
        "rsi": 50.0,
        "macd": {"macd": 0.0, "signal": 0.0, "histogram": 0.0, "status": "no_data"},
        "bollinger": {"upper": 100.0, "middle": 95.0, "lower": 90.0, "position": "unknown"},
        "support": 90.0,
        "resistance": 110.0,
        "trend": "unknown",
        "technical_signal": "neutral_consolidation",
        "bull_score": 0.5,
        "bear_score": 0.5,
        "amplitude": 20.0, 
        "sr_levels": []
    }

    # Si pas de données, retourner default
    if prices_data is None or prices_data.empty:
        logger.warning(f"⚠️ Pas de données OHLCV pour {symbol}")
        return default_response
    
    try:
        # Extraire les closes
        if isinstance(prices_data, pd.DataFrame):
            if "Close" not in prices_data.columns:
                logger.warning(f"⚠️ Colonne 'Close' manquante dans prices_data")
                return default_response
            closes = prices_data["Close"]
        else:
            closes = prices_data
        
        # S'assurer que c'est une Series de floats
        closes = pd.Series(closes, dtype=float)
        
        if closes.empty or len(closes) < 2:
            logger.warning(f"⚠️ Pas assez de données (min 2 closes)")
            return default_response
        
        # === Calculer tous les indicateurs ===
        
        # 1. RSI
        rsi = calculate_rsi(closes, period=14)
        
        # 2. MACD
        macd_data = calculate_macd(closes)
        
        # 3. Bollinger Bands
        bollinger_data = calculate_bollinger_bands(closes, period=20)
        
        # 4. Support/Resistance
        sr_data = calculate_support_resistance(closes, window=20)
        
        # 5. Trend
        trend = determine_trend(closes, period=50)
        
        # === Scorer ===
        
        bull_score = 0.0
        bear_score = 0.0
        
        # RSI scoring
        if rsi < 30:
            bull_score += 0.3
        elif rsi > 70:
            bear_score += 0.3
        
        # MACD scoring
        if macd_data["status"] == "bullish_crossover":
            bull_score += 0.25
        elif macd_data["status"] == "bullish_momentum":
            bull_score += 0.15
        elif macd_data["status"] == "bearish_crossover":
            bear_score += 0.25
        elif macd_data["status"] == "bearish_momentum":
            bear_score += 0.15
        
        # Bollinger scoring
        if bollinger_data["position"] == "at_lower_band":
            bull_score += 0.2
        elif bollinger_data["position"] == "at_upper_band":
            bear_score += 0.2
        
        # Trend scoring
        if trend == "bullish":
            bull_score += 0.25
        elif trend == "bearish":
            bear_score += 0.25
        
        # Signal final
        if bull_score > bear_score + 0.2:
            technical_signal = "strong_bullish_reversal"
        elif bull_score > bear_score:
            technical_signal = "weak_bullish"
        elif bear_score > bull_score + 0.2:
            technical_signal = "strong_bearish_reversal"
        elif bear_score > bull_score:
            technical_signal = "weak_bearish"
        else:
            technical_signal = "neutral_consolidation"
        
        # === Build response ===
        
        response = {
            "rsi": rsi,
            "macd": macd_data,
            "bollinger": bollinger_data,
            "support": sr_data["support"],
            "resistance": sr_data["resistance"],
            "trend": trend,
            "technical_signal": technical_signal,
            "bull_score": min(bull_score, 1.0),
            "bear_score": min(bear_score, 1.0),
            "sr_levels": sr_data["levels"],
            "amplitude": float(sr_data["resistance"] - sr_data["support"]),
            "sr_levels": sr_data["levels"]
        }
        
        logger.info(
            f"✅ Technical Analysis {symbol}: "
            f"RSI={rsi:.1f} | MACD={macd_data['status']} | "
            f"Bollinger={bollinger_data['position']} | Trend={trend} | "
            f"Signal={technical_signal}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Erreur analyse technique {symbol}: {e}", exc_info=True)
        return default_response
    