"""
NOUVEAU GRAPH OPTIMISÉ
- 12 agents dans le bon ordre
- Validation AVANT exécution
- Avec fallback intelligent
"""

from langgraph.graph import StateGraph, END
from ..shared.state import AgentState

# Import de TOUS les agents
from ..agents.retriever import get_market_data
from ..agents.fundamental_screener import screen_fundamentals
from ..agents.technician import analyze_technical
from ..agents.sentiment_timeseries import scan_sentiment_timeseries
from ..agents.market_regime_detector import detect_market_regime_agent
from ..agents.portfolio_analyzer import analyze_portfolio
from ..agents.strategy_builder import build_strategy
from ..agents.risk_manager import validate_strategy
from ..executor.trade_runner import execute_trade

import logging

logger = logging.getLogger("graph")


def route_after_fundamental_screening(state: AgentState) -> str:
    """
    Route conditionnel après screening fondamental.
    Si FAIL fondamental → SKIP tout l'analyse
    Si PASS → Continue vers technical
    """
    
    fundamental_pass = state.get('fundamental_pass', True)
    
    if not fundamental_pass:
        logger.warning(f"⚠️ Fundamental screening FAILED pour {state.get('symbol')} - SKIP")
        return "end_reject"  # Terminus
    
    return "technical"  # Continue vers technical analysis


def route_after_strategy(state: AgentState) -> str:
    """
    Route après construction de la stratégie.
    BUY/SELL → Vers Risk Validator
    HOLD → Vers end (pas de validation d'ordre)
    """
    
    decision = state.get('decision', 'hold')
    
    if decision == "hold":
        logger.info(f"ℹ️ Décision HOLD - pas d'ordre à valider")
        return "end_hold"
    
    return "risk_validator"


def route_after_risk_validation(state: AgentState) -> str:
    """
    Route après validation de risque.
    Approved → Execute
    Rejected → End reject
    """
    
    risk_approved = state.get('approved', False)
    
    if not risk_approved:
        logger.warning(f"❌ Risk validation REJECTED - pas d'exécution")
        return "end_reject"
    
    return "executor"


def route_at_start(state: AgentState) -> str:
    """
    Route au démarrage: gestion des positions vs nouvelles opportunités.
    Si position existante: Analyser gestion
    Si pas de position: Analyser pour BUY
    """
    
    position_qty = state.get('position_qty', 0)
    
    # TODO: Implémenter position management workflow (close/modify)
    # Pour maintenant: tout le monde passe par le même workflow
    
    return "fundamental"


def build_graph():
    """Construit le graphe LangGraph optimisé."""
    
    workflow = StateGraph(AgentState)
    
    # ========== NŒUDS ==========
    
    # Phase 0: Retriever (données de base)
    workflow.add_node("retriever", get_market_data)
    
    # Phase 1: Screening
    workflow.add_node("fundamental", screen_fundamentals)
    workflow.add_node("technical", analyze_technical)
    workflow.add_node("sentiment", scan_sentiment_timeseries)
    
    # Phase 2: Context Global
    workflow.add_node("regime", detect_market_regime_agent)
    
    # Phase 3: Portfolio Intelligence
    workflow.add_node("portfolio", analyze_portfolio)
    
    # Phase 4: Decision
    workflow.add_node("strategy", build_strategy)
    
    # Phase 5: Risk Management
    workflow.add_node("risk_validator", validate_strategy)
    
    # Phase 6: Execution
    workflow.add_node("executor", execute_trade)
    
    # ========== EDGES ==========
    
    # Entry point
    workflow.set_entry_point("retriever")
    
    # Retriever → Fundamental (screening)
    workflow.add_edge("retriever", "fundamental")
    
    # Fundamental → Conditional (PASS/FAIL)
    workflow.add_conditional_edges(
        "fundamental",
        route_after_fundamental_screening,
        {
            "technical": "technical",
            "end_reject": END
        }
    )
    
    # Technical → Sentiment (parallèle dans le futur)
    workflow.add_edge("technical", "sentiment")
    
    # Sentiment → Regime (contexte global)
    workflow.add_edge("sentiment", "regime")
    
    # Regime → Portfolio (analyse diversification)
    workflow.add_edge("regime", "portfolio")
    
    # Portfolio → Strategy (construction complète)
    workflow.add_edge("portfolio", "strategy")
    
    # Strategy → Conditional (HOLD/BUY/SELL)
    workflow.add_conditional_edges(
        "strategy",
        route_after_strategy,
        {
            "risk_validator": "risk_validator",
            "end_hold": END,
            "end_reject": END
        }
    )
    
    # Risk Validator → Conditional (APPROVED/REJECTED)
    workflow.add_conditional_edges(
        "risk_validator",
        route_after_risk_validation,
        {
            "executor": "executor",
            "end_reject": END
        }
    )
    
    # Executor → End
    workflow.add_edge("executor", END)
    
    logger.info("✅ Graph compilé avec 8 agents (retriever, fundamental, technical, sentiment, regime, portfolio, strategy, validator)")
    
    return workflow.compile()


# ========== LEGACY SUPPORT ==========
# Ancien format de graph.py (pour compatibilité)

def build_legacy_graph():
    """Ancien graphe (deprecated, garde pour compatibilité)."""
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("retriever", get_market_data)
    workflow.add_node("social", scan_sentiment_timeseries)  # Ancien nom
    workflow.add_node("tech", analyze_technical)
    workflow.add_node("analyst", build_strategy)  # Ancien Analyst → nouveau Strategy
    workflow.add_node("risk", validate_strategy)
    workflow.add_node("executor", execute_trade)
    
    workflow.set_entry_point("retriever")
    workflow.add_edge("retriever", "social")
    workflow.add_edge("social", "tech")
    workflow.add_edge("tech", "analyst")
    workflow.add_edge("analyst", "risk")
    workflow.add_edge("risk", "executor")
    workflow.add_edge("executor", END)
    
    return workflow.compile()
