"""
Strategy Builder Agent (Replaces simple Analyst)
- Prend décision finale avec Chain of Thought explicite
- Définit entry/TP/SL multiples et raison
- Retourne stratégie complète (pas juste BUY/SELL/HOLD)
"""

import json
import re
import logging
from typing import Dict, Any
from ..shared.state import AgentState
from ..shared.llm_client import get_llm

logger = logging.getLogger("strategy_builder")


def build_strategy(state: AgentState) -> Dict[str, Any]:
    """Agent principal: construit stratégie d'entrée/sortie avec raisonnement."""
    
    symbol = state.get('symbol', 'UNKNOWN')
    
    print(f"🧠 [Strategy Builder] Construction stratégie pour {symbol}...")
    
    # 1. Récupère données de tous les agents précédents
    price = state.get('price', 0)
    rsi = state.get('rsi', 50)
    macd_status = state.get('macd', {}).get('status', 'neutral')
    bollinger_position = state.get('bollinger', {}).get('position', 'middle')
    support = state.get('support', price * 0.95)
    resistance = state.get('resistance', price * 1.05)
    trend = state.get('trend', 'unknown')
    
    sentiment_score = state.get('sentiment_score', 0)
    sentiment_trend = state.get('sentiment_trend', 'neutral')
    
    technical_signal = state.get('technical_signal', 'neutral')
    
    fundamental_pass = state.get('fundamental_pass', True)
    fundamental_score = state.get('fundamental_score', 0.5)
    
    market_regime = state.get('market_regime', 'neutral')
    position_multiplier = state.get('position_multiplier', 1.0)
    
    portfolio_can_add = state.get('can_add', True)
    
    position_qty = state.get('position_qty', 0)
    
    # 2. Chain of Thought explicite
    bull_arguments = []
    bear_arguments = []
    
    # --- BULL ARGUMENTS ---
    if sentiment_score > 0.4:
        bull_arguments.append(f"Sentiment social fort ({sentiment_score:.2f}) - bullish conviction")
    
    if "bullish" in trend.lower():
        bull_arguments.append(f"Tendance technique {trend} - momentum haussier")
    
    if rsi < 40:
        bull_arguments.append(f"RSI={rsi:.0f} - zone d'achat favorable (< 40)")
    
    if technical_signal in ["strong_bullish_reversal", "bullish_trend"]:
        bull_arguments.append(f"Signal technique {technical_signal} - setup d'entrée qualité")
    
    if sentiment_trend in ["accelerating_bullish", "bullish"]:
        bull_arguments.append(f"Sentiment en {sentiment_trend} - confirmation du setup")
    
    # --- BEAR ARGUMENTS ---
    if sentiment_score < -0.4:
        bear_arguments.append(f"Sentiment social négatif ({sentiment_score:.2f}) - risque baissier")
    
    if "bearish" in trend.lower():
        bear_arguments.append(f"Tendance technique {trend} - momentum baissier")
    
    if rsi > 60:
        bear_arguments.append(f"RSI={rsi:.0f} - zone de surachat (> 60)")
    
    if technical_signal in ["strong_bearish_reversal", "bearish_trend"]:
        bear_arguments.append(f"Signal technique {technical_signal} - setup de vente potentielle")
    
    if market_regime == "risk_off":
        bear_arguments.append(f"Régime marché {market_regime} - conditions défavorables")
    
    if not fundamental_pass:
        bear_arguments.append(f"Screening fondamental échoué (score: {fundamental_score:.2f})")
    
    if not portfolio_can_add and position_qty == 0:
        bear_arguments.append("Portfolio constraint: Ne pas ajouter selon analyse diversification")
    
    # 3. Synthèse et décision
    bull_score = len(bull_arguments)
    bear_score = len(bear_arguments)
    
    # Règles de décision stricts
    decision = "hold"  # Par défaut
    entry_signal_strength = 0
    
    if bull_score >= 3 and bear_score <= 1:
        decision = "buy"
        entry_signal_strength = min(bull_score / (bull_score + bear_score + 0.1), 1.0)
    elif bear_score >= 3 and bull_score <= 1 and position_qty > 0:
        decision = "sell"
        entry_signal_strength = min(bear_score / (bear_score + bull_score + 0.1), 1.0)
    elif bull_score > bear_score + 1:
        decision = "buy"
        entry_signal_strength = min(bull_score / (bull_score + bear_score + 0.1), 1.0)
    elif bear_score > bull_score + 1 and position_qty > 0:
        decision = "sell"
        entry_signal_strength = min(bear_score / (bear_score + bull_score + 0.1), 1.0)
    else:
        decision = "hold"
        entry_signal_strength = 0.5
    
    # 4. Construction de la stratégie détaillée
    
    if decision == "buy":
        strategy = _build_buy_strategy(
            symbol=symbol,
            price=price,
            support=support,
            resistance=resistance,
            rsi=rsi,
            market_regime=market_regime,
            position_multiplier=position_multiplier,
            signal_strength=entry_signal_strength
        )
    
    elif decision == "sell":
        strategy = _build_sell_strategy(
            symbol=symbol,
            price=price,
            position_qty=position_qty,
            avg_entry=state.get('avg_entry_price', price),
            resistance=resistance,
            signal_strength=entry_signal_strength
        )
    
    else:  # HOLD
        strategy = {
            "action": "hold",
            "reason": "Signaux mixtes - attendre clarification du marché",
            "conviction": 0.5,
            "entry_price": None,
            "tp_targets": [],
            "sl_level": None,
            "position_size": 0,
            "time_horizon": "wait"
        }
    
    # 5. Synthèse finale
    result = {
        "decision": decision,
        "strategy": strategy,
        "bull_arguments": bull_arguments,
        "bear_arguments": bear_arguments,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "conviction": entry_signal_strength,
        "market_regime": market_regime,
        "position_multiplier": position_multiplier,
        "reasoning_summary": f"Bull ({bull_score}) vs Bear ({bear_score}) → {decision.upper()}"
    }
    
    print(f"  Decision: {decision.upper()} | Bull: {bull_score} | Bear: {bear_score} | Conviction: {entry_signal_strength:.2f}")
    
    return result


def _build_buy_strategy(
    symbol: str,
    price: float,
    support: float,
    resistance: float,
    rsi: float,
    market_regime: str,
    position_multiplier: float,
    signal_strength: float
) -> Dict[str, Any]:
    """Construit stratégie d'achat avec TP/SL multiples."""
    
    # Calcul des niveaux
    # Entry: légèrement en-dessous du prix actuel (limit order)
    entry_price = price * 0.98  # 2% de discount
    
    # Stop Loss: sous le support ou -3% du prix, au plus proche
    sl_level = min(support * 0.97, price * 0.97)
    
    # Take Profits multiples:
    # TP1: +2% (rapide)
    # TP2: +5% (intermédiaire)
    # TP3: +8-10% (long term)
    tp_targets = [
        {"level": price * 1.02, "pct": 2, "description": "Quick profit - sell 30%"},
        {"level": price * 1.05, "pct": 5, "description": "Medium term - sell 40%"},
        {"level": resistance * 1.01, "pct": 8, "description": "Breakout target - sell 30%"}
    ]
    
    # Position sizing
    risk_reward = (entry_price - sl_level) / (tp_targets[2]["level"] - entry_price) if entry_price != sl_level else 1.0
    
    # Ajuste par régime marché
    base_position_size = 10  # Shares (default)
    
    if "risk_on" in market_regime:
        position_size = int(base_position_size * position_multiplier * 1.2)
    elif "risk_off" in market_regime:
        position_size = int(base_position_size * position_multiplier * 0.6)
    else:
        position_size = int(base_position_size * position_multiplier)
    
    # Time horizon: 5-14 jours pour swing trade
    time_horizon = "5-14 days (swing trade)"
    
    return {
        "action": "buy",
        "reason": f"Bullish setup: Support zone ({support:.2f}) + Positive momentum",
        "conviction": signal_strength,
        "entry_price": entry_price,
        "entry_type": "limit",
        "tp_targets": tp_targets,
        "sl_level": sl_level,
        "risk_reward_ratio": risk_reward,
        "position_size": position_size,
        "time_horizon": time_horizon,
        "order_type": "bracket_order",
        "notes": [
            f"Entry: {entry_price:.2f} (limit, -2%)",
            f"Stop Loss: {sl_level:.2f} (-3%)",
            f"Risk/Reward: {risk_reward:.2f}",
            f"Régime: {market_regime} → Multiplier: {position_multiplier:.1f}x"
        ]
    }


def _build_sell_strategy(
    symbol: str,
    price: float,
    position_qty: int,
    avg_entry: float,
    resistance: float,
    signal_strength: float
) -> Dict[str, Any]:
    """Construit stratégie de vente."""
    
    # P&L actuel
    pnl_pct = ((price - avg_entry) / avg_entry * 100) if avg_entry > 0 else 0
    
    return {
        "action": "sell",
        "reason": f"Bearish setup or Stop Loss trigger (P&L: {pnl_pct:+.1f}%)",
        "conviction": signal_strength,
        "exit_price": price,
        "exit_type": "market",
        "position_size": position_qty,
        "current_pnl_pct": pnl_pct,
        "average_entry": avg_entry,
        "time_horizon": "immediate",
        "order_type": "market_order",
        "notes": [
            f"Current P&L: {pnl_pct:+.1f}%",
            f"Entry was: {avg_entry:.2f}",
            f"Exit at: {price:.2f}",
            "Fermeture de position pour protéger gains/limiter pertes"
        ]
    }
