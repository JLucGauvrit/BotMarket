from typing import TypedDict, Literal, Any, Dict

class AgentState(TypedDict):
    symbol: str
    price: float
    position_qty: int
    cash: float
    prices_df: Any

    # Rapports des analystes (remplis en parallèle)
    technical_report: Dict[str, Any]
    fundamental_report: Dict[str, Any]
    sentiment_report: Dict[str, Any]
    market_regime: Dict[str, Any]
    portfolio_report: Dict[str, Any]

    # Décision du Head Trader
    decision: Literal["buy", "sell", "hold"]
    strategy: Dict[str, Any]
    reasoning: str
    
    # Validation
    approved: bool
    