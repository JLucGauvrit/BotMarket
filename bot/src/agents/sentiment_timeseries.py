"""
Sentiment Time-Series Agent V2
- Score de sentiment avec historique (7-14 jours)
- Détecte tendance du sentiment (accelerating bullish, mass exit, etc.)
- Pondère par engagement/volume
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import re
from ..shared.state import AgentState
from ..shared.llm_client import get_llm

logger = logging.getLogger("sentiment_ts")

# Simulation de DB locale (en prod: Redis/SQLite)
SENTIMENT_HISTORY = {}  # {symbol: [(timestamp, score, source, engagement)]}

def store_sentiment(symbol: str, score: float, source: str, engagement: int = 0):
    """
    Stocke un score de sentiment pour un symbole avec timestamp et source.

    Args:
        symbol (str): Symbole de l'actif.
        score (float): Score de sentiment (-1.0 à 1.0).
        source (str): Source du score (ex: 'reddit', 'twitter').
        engagement (int): Niveau d'engagement associé (par défaut 0).

    Effects:
        - Modifie la variable globale SENTIMENT_HISTORY.
    """
    if symbol not in SENTIMENT_HISTORY:
        SENTIMENT_HISTORY[symbol] = []
    
    SENTIMENT_HISTORY[symbol].append({
        "timestamp": datetime.now(),
        "score": score,
        "source": source,
        "engagement": engagement
    })
    
    # Garde seulement 14 jours
    cutoff = datetime.now() - timedelta(days=14)
    SENTIMENT_HISTORY[symbol] = [
        s for s in SENTIMENT_HISTORY[symbol] 
        if s["timestamp"] > cutoff
    ]


def get_sentiment_history(symbol: str, days: int = 7) -> List[Dict]:
    """
    Récupère l'historique des scores de sentiment pour un symbole.

    Args:
        symbol (str): Symbole de l'actif.
        days (int): Fenêtre de recherche en jours (par défaut 7).

    Returns:
        List[Dict]: Liste de scores horodatés.
    """
    if symbol not in SENTIMENT_HISTORY:
        return []
    
    cutoff = datetime.now() - timedelta(days=days)
    return [
        s for s in SENTIMENT_HISTORY[symbol]
        if s["timestamp"] > cutoff
    ]


def calculate_sentiment_trend(history: List[Dict]) -> Dict[str, Any]:
    """
    Calcule la tendance du sentiment à partir d'un historique.

    Args:
        history (List[Dict]): Liste de scores horodatés.

    Returns:
        Dict[str, Any]: Dictionnaire avec trend, slope, conviction, amplitude, etc.
    """
    
    if len(history) < 2:
        return {
            "trend": "neutral", 
            "slope": 0.0, 
            "conviction": 0.0,
            "amplitude": 0.0,      # <--- Clé manquante ajoutée
            "avg_7d": 0.0,         # <--- Clé manquante ajoutée
            "current_score": 0.0
        }
    
    scores = [h["score"] for h in history]
    
    # Slope = regression simple sur scores
    n = len(scores)
    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(scores) / n
    
    numerator = sum((x[i] - mean_x) * (scores[i] - mean_y) for i in range(n))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
    
    slope = numerator / denominator if denominator != 0 else 0
    
    # Tendance
    if slope > 0.08 and mean_y > 0.3:
        trend = "accelerating_bullish"
    elif slope > 0.03 and mean_y > 0:
        trend = "bullish"
    elif slope < -0.08 and mean_y < -0.3:
        trend = "accelerating_bearish"
    elif slope < -0.03 and mean_y < 0:
        trend = "bearish"
    else:
        trend = "neutral"
    
    # Conviction = amplitude du changement + stabilité
    min_score = min(scores)
    max_score = max(scores)
    amplitude = max_score - min_score
    
    conviction = min(abs(slope) * 10 + amplitude * 0.3, 1.0)
    
    return {
        "trend": trend,
        "slope": slope,
        "amplitude": amplitude,
        "conviction": conviction,
        "current_score": scores[-1] if scores else 0,
        "avg_7d": sum(scores) / len(scores)
    }


def scan_reddit_sentiment(symbol: str, subreddit: str = "cryptocurrency") -> Dict[str, Any]:
    """
    Analyse le sentiment Reddit pour un symbole donné.

    Args:
        symbol (str): Symbole de l'actif.
        subreddit (str): Nom du subreddit à analyser.

    Returns:
        Dict[str, Any]: Score de sentiment, engagement, source, etc.
    """
    print(f"🔴 [Reddit] Scanning {symbol} on r/{subreddit}...")
    
    try:
        # En prod: utiliser PRAW + Pushshift API
        # Pour maintenant: fallback intelligent
        
        # Format simplifié - idéalement tu utilises Pushshift/Reddit API
        query = f"{symbol} site:reddit.com/r/{subreddit}"
        
        # Mock data (replace avec vrai Reddit API)
        mock_sentiment = {
            "DOGE": 0.65,  # Très bullish
            "SHIB": 0.45,  # Modérément bullish
            "BTC": 0.55,   # Neutre-bullish
            "ETH": 0.50    # Neutre
        }
        
        score = mock_sentiment.get(symbol.upper(), 0.5)
        engagement = {"DOGE": 2500, "SHIB": 1200, "BTC": 3000}.get(symbol.upper(), 500)
        
        return {
            "score": score,
            "engagement": engagement,
            "posts_analyzed": 50,
            "source": "reddit"
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur Reddit: {e}")
        return {"score": 0.5, "engagement": 0, "posts_analyzed": 0, "source": "error"}


def scan_twitter_sentiment(symbol: str) -> Dict[str, Any]:
    """
    Analyse le sentiment Twitter/X pour un symbole donné.

    Args:
        symbol (str): Symbole de l'actif.

    Returns:
        Dict[str, Any]: Score de sentiment, engagement, source, etc.
    """
    print(f"🐦 [Twitter/X] Scanning {symbol}...")
    
    try:
        # Mock pour test - en prod: Tweepy API avec Academic access
        mock_sentiment = {
            "DOGE": 0.72,  # Community très engagée
            "SHIB": 0.38,  # Mixed signals
            "BTC": 0.58,   # Stable
            "ETH": 0.52    # Légèrement bullish
        }
        
        score = mock_sentiment.get(symbol.upper(), 0.5)
        engagement = {"DOGE": 4500, "SHIB": 800, "BTC": 5200}.get(symbol.upper(), 600)
        
        return {
            "score": score,
            "engagement": engagement,
            "tweets_analyzed": 150,
            "source": "twitter"
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur Twitter: {e}")
        return {"score": 0.5, "engagement": 0, "tweets_analyzed": 0, "source": "error"}


def aggregate_sentiment_sources(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Agrège les scores de sentiment multi-source pondérés par engagement.

    Args:
        sources (List[Dict[str, Any]]): Liste de scores de différentes sources.

    Returns:
        Dict[str, Any]: Score agrégé, confiance, nombre de sources.
    """
    
    if not sources:
        return {"score": 0.5, "weighted_score": 0.5, "confidence": 0}
    
    # Poids par engagement
    total_engagement = sum(s.get("engagement", 0) for s in sources)
    
    weighted_sum = 0
    weights = []
    
    for source in sources:
        engagement = source.get("engagement", 0)
        score = source.get("score", 0.5)
        
        # Plus d'engagement = plus de poids
        weight = (engagement + 100) / (total_engagement + len(sources) * 100)  # Lissage
        weighted_sum += score * weight
        weights.append(weight)
    
    weighted_score = weighted_sum / len(sources) if sources else 0.5
    
    # Confiance = mean weights (si tous les sources d'accord = haute confiance)
    confidence = 1.0 - (max(weights) - min(weights)) if weights else 0
    
    logger.info(f"  Weighted sentiment: {weighted_score:.3f} | Confidence: {confidence:.2f}")
    
    return {
        "score": weighted_score,
        "weighted_score": weighted_score,
        "confidence": confidence,
        "sources": len(sources)
    }

def analyze_with_llm(symbol: str, sentiment_score: float, trend: Dict, sources_count: int) -> Dict[str, Any]:
    """
    Génère une analyse de contexte via LLM à partir du score de sentiment et de la tendance.

    Args:
        symbol (str): Symbole de l'actif.
        sentiment_score (float): Score agrégé de sentiment.
        trend (Dict): Dictionnaire de tendance calculée.
        sources_count (int): Nombre de sources agrégées.

    Returns:
        Dict[str, Any]: Contexte textuel généré et flag d'analyse LLM.
    """
    
    try:
        llm = get_llm(temperature=0.1)
        
        prompt = f"""
Tu es un analyste en sentiment de marché.

ASSET: {symbol}
SENTIMENT SCORE: {sentiment_score:.2f} (-1.0 pessimiste à 1.0 optimiste)
TREND: {trend.get('trend', 'unknown')}
CONVICTION: {trend.get('conviction', 0):.2f}
SOURCES: {sources_count}

Tâche: Générer un CONTEXTE COURT (2 phrases) expliquant le sentiment.

Exemples:
- 0.75 + accelerating_bullish = "Community très engagée, momentum haussier confirmé"
- -0.65 + bearish = "Préoccupations majeures, sentiment négatif dominant"
- 0.05 + neutral = "Marchés indécis, manque de conviction"

Réponds UNIQUEMENT le contexte (pas plus de 30 mots).
"""
        
        message = llm.invoke(prompt)
        
        # --- FIX TYPAGE PYLANCE ---
        # content peut être str ou list (multimodal). On sécurise.
        raw_content = message.content
        
        if isinstance(raw_content, list):
            # Si c'est une liste, on joint les éléments (cas rare)
            text_content = " ".join([str(item) for item in raw_content])
        else:
            # Sinon on force en string pour être sûr
            text_content = str(raw_content)
            
        return {
            "context": text_content.strip()[:150],
            "llm_analysis": True
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur LLM sentiment: {e}")
        return {
            "context": "Analyse technique non disponible",
            "llm_analysis": False
        }
    

def scan_sentiment_timeseries(state: AgentState) -> Dict[str, Any]:
    """
    Agent principal de collecte et d'analyse du sentiment multi-source avec historique.

    Args:
        state (AgentState): Etat de l'agent, doit contenir 'symbol'.

    Returns:
        Dict[str, Any]: Résultat de l'analyse de sentiment (score, trend, contexte, etc.).

    Effects:
        - Appels API externes (Reddit, Twitter/X, LLM).
        - Logs d'information et d'erreur.
    """
    
    symbol = state.get('symbol', 'UNKNOWN')
    print(f"💭 [Sentiment TS] Analyse pour {symbol}...")
    
    # 1. Collecte multi-source
    reddit_sentiment = scan_reddit_sentiment(symbol)
    twitter_sentiment = scan_twitter_sentiment(symbol)
    
    sources = [reddit_sentiment, twitter_sentiment]
    
    # 2. Agrégation pondérée
    aggregated = aggregate_sentiment_sources(sources)
    sentiment_score = aggregated["weighted_score"]
    
    # 3. Stockage historique
    store_sentiment(symbol, sentiment_score, "aggregated", 
                   sum(s.get("engagement", 0) for s in sources))
    
    # 4. Analyse de tendance
    history = get_sentiment_history(symbol, days=7)
    trend = calculate_sentiment_trend(history)
    
    # 5. Contexte LLM
    llm_analysis = analyze_with_llm(symbol, sentiment_score, trend, len(sources))
    
    result = {
        "sentiment_score": sentiment_score,
        "trend": trend["trend"],
        "slope": trend["slope"],
        "conviction": trend["conviction"],
        "amplitude": trend["amplitude"],
        "avg_7d": trend["avg_7d"],
        "current_score": sentiment_score,
        "sources": {
            "reddit": reddit_sentiment,
            "twitter": twitter_sentiment
        },
        "aggregation_confidence": aggregated["confidence"],
        "context": llm_analysis["context"],
        "history_length": len(history)
    }
    
    print(f"  Score: {sentiment_score:.2f} | Trend: {trend['trend']} | Conviction: {trend['conviction']:.2f}")
    
    return result
