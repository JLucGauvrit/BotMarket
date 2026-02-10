from typing import TypedDict, List, Literal, Optional, Any

class AgentState(TypedDict):
    symbol: str
    price: float
    position_qty: int
    
    # Ajout critique pour le Technicien
    prices_df: Any  # pandas.DataFrame
    
    social_sentiment: float
    social_summary: str
    
    # Analyse Technique
    rsi: float
    trend: str
    
    # Décision Finale
    decision: Literal["buy", "sell", "hold"]
    reasoning: str
    