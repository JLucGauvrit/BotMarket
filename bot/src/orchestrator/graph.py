from langgraph.graph import StateGraph, END
from ..shared.state import AgentState
from ..agents.retriever import get_market_data
from ..agents.social_scanner import scan_social_media
from ..agents.technician import calculate_indicators
from ..agents.analyst import sentiment_analyst
from ..agents.risk_manager import validate_risk
from ..executor.trade_runner import execute_trade

def build_graph():
    workflow = StateGraph(AgentState)

    # 1. Ajout des Nœuds
    workflow.add_node("retriever", get_market_data)      # Gateway
    workflow.add_node("social", scan_social_media)       # X/Reddit
    workflow.add_node("tech", calculate_indicators)      # RSI
    workflow.add_node("analyst", sentiment_analyst)      # Qwen
    workflow.add_node("risk", validate_risk)             # Stop-loss
    workflow.add_node("executor", execute_trade)         # Gateway Order

    # 2. Définition du Flux (Parallélisme possible !)
    workflow.set_entry_point("retriever")
    
    # On lance le scan social et l'analyse technique APRÈS avoir eu le prix
    workflow.add_edge("retriever", "social")
    workflow.add_edge("retriever", "tech")
    
    # L'analyste attend les deux (Social + Tech)
    workflow.add_edge("social", "analyst")
    workflow.add_edge("tech", "analyst")
    
    # Validation et Exécution
    workflow.add_edge("analyst", "risk")
    workflow.add_edge("risk", "executor")
    workflow.add_edge("executor", END)

    return workflow.compile()
