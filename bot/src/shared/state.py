from typing import TypedDict, List, Literal, Optional

class AgentState(TypedDict):
    symbol: str
    price: float
    position_qty: int
    
    social_sentiment: float  # Score de -1 (Bearish) à 1 (Bullish)
    social_summary: str      # Résumé des tweets/posts
    
    # Analyse Technique
    rsi: float
    trend: str
    
    # Décision Finale
    decision: Literal["buy", "sell", "hold"]
    reasoning: str
