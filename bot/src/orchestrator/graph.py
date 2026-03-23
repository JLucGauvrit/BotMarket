from langgraph.graph import StateGraph, END
from ..shared.state import AgentState
from ..agents.retriever import get_market_data
from ..agents.fundamental_screener import screen_fundamentals
from ..agents.technician import analyze_technical
from ..agents.sentiment_timeseries import scan_sentiment_timeseries
from ..agents.market_regime_detector import detect_market_regime_agent
from ..agents.portfolio_analyzer import analyze_portfolio
from ..agents.strategy_builder import build_strategy
from ..agents.risk_manager import validate_strategy
from ..executor.trade_runner import execute_trade

def route_after_head_trader(state: AgentState) -> str:
    if state.get('decision', 'hold') == "hold":
        return "end_hold"
    return "risk_validator"

def route_after_risk(state: AgentState) -> str:
    if not state.get('approved', False):
        return "end_reject"
    return "executor"

def build_graph():
    workflow = StateGraph(AgentState)
    
    # Ajout des noeuds
    workflow.add_node("retriever", get_market_data)
    workflow.add_node("technical", analyze_technical)
    workflow.add_node("fundamental", screen_fundamentals)
    workflow.add_node("sentiment", scan_sentiment_timeseries)
    workflow.add_node("regime", detect_market_regime_agent)
    workflow.add_node("portfolio", analyze_portfolio)
    workflow.add_node("head_trader", build_strategy)
    workflow.add_node("risk_validator", validate_strategy)
    workflow.add_node("executor", execute_trade)
    
    # 1. Point d'entrée
    workflow.set_entry_point("retriever")
    
    # 2. Exécution parallèle des analystes (Fan-out)
    workflow.add_edge("retriever", "technical")
    workflow.add_edge("retriever", "fundamental")
    workflow.add_edge("retriever", "sentiment")
    workflow.add_edge("retriever", "regime")
    
    # 3. Convergence vers l'analyse de portefeuille (Fan-in)
    workflow.add_edge("technical", "portfolio")
    workflow.add_edge("fundamental", "portfolio")
    workflow.add_edge("sentiment", "portfolio")
    workflow.add_edge("regime", "portfolio")
    
    # 4. Le Head Trader tranche le débat
    workflow.add_edge("portfolio", "head_trader")
    
    # 5. Routage conditionnel final
    workflow.add_conditional_edges("head_trader", route_after_head_trader, {
        "risk_validator": "risk_validator",
        "end_hold": END,
        "end_reject": END
    })
    workflow.add_conditional_edges("risk_validator", route_after_risk, {
        "executor": "executor",
        "end_reject": END
    })
    workflow.add_edge("executor", END)
    
    return workflow.compile()
