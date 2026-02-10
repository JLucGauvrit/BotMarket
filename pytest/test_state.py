"""
Tests pour le module shared.state (AgentState)
"""

import pytest
from typing import Any
from bot.src.shared.state import AgentState


class TestAgentState:
    """Teste la structure et la validation de AgentState."""
    
    def test_agent_state_creation(self):
        """Vérifie qu'on peut créer une AgentState valide."""
        state: AgentState = {
            'symbol': 'BTC/USD',
            'price': 45000.0,
            'position_qty': 1,
            'prices_df': None,
            'social_sentiment': 0.75,
            'social_summary': 'Bullish',
            'rsi': 65.0,
            'trend': 'UP',
            'decision': 'buy',
            'reasoning': 'Strong technical signals'
        }
        assert state['symbol'] == 'BTC/USD'
        assert state['price'] == 45000.0
        assert state['decision'] == 'buy'
    
    def test_agent_state_with_defaults(self):
        """Teste AgentState avec valeurs minimales."""
        state: AgentState = {
            'symbol': 'ETH/USD',
            'price': 2500.0,
            'position_qty': 0,
            'prices_df': None,
            'social_sentiment': 0.0,
            'social_summary': 'Neutral',
            'rsi': 50.0,
            'trend': 'NEUTRAL',
            'decision': 'hold',
            'reasoning': 'Waiting for signals'
        }
        assert state['decision'] == 'hold'
        assert state['position_qty'] == 0
    
    def test_agent_state_sell_decision(self):
        """Teste une décision de vente."""
        state: AgentState = {
            'symbol': 'DOGE/USD',
            'price': 0.35,
            'position_qty': 100,
            'prices_df': None,
            'social_sentiment': -0.5,
            'social_summary': 'Bearish sentiment',
            'rsi': 35.0,
            'trend': 'DOWN',
            'decision': 'sell',
            'reasoning': 'Price breakdown detected'
        }
        assert state['decision'] == 'sell'
        assert state['price'] == 0.35
        assert state['social_sentiment'] < 0
    
    def test_agent_state_value_extraction(self):
        """Teste l'accès aux valeurs de l'état."""
        state: AgentState = {
            'symbol': 'SOL/USD',
            'price': 200.0,
            'position_qty': 5,
            'prices_df': None,
            'social_sentiment': 0.6,
            'social_summary': 'Moderate bullish',
            'rsi': 60.0,
            'trend': 'UP',
            'decision': 'buy',
            'reasoning': 'Momentum building'
        }
        
        assert state.get('symbol') == 'SOL/USD'
        assert state.get('price', 0) == 200.0
        assert state.get('position_qty', 0) == 5
        assert state.get('unknown_key', 'default') == 'default'
    
    def test_agent_state_extreme_values(self):
        """Teste les valeurs extrêmes (prix très hauts/bas)."""
        state: AgentState = {
            'symbol': 'SHIB/USD',
            'price': 0.000001,  # Très petit prix
            'position_qty': 1_000_000,  # Très grande quantité
            'prices_df': None,
            'social_sentiment': 1.0,  # Maximum
            'social_summary': 'Extreme bullish',
            'rsi': 99.0,  # Overbought
            'trend': 'UP',
            'decision': 'buy',
            'reasoning': 'Pump signal'
        }
        assert state['price'] == 0.000001
        assert state['position_qty'] == 1_000_000
        assert state['social_sentiment'] == 1.0
    
    def test_agent_state_negative_sentiment(self):
        """Teste les sentiments négatifs."""
        state: AgentState = {
            'symbol': 'XRP/USD',
            'price': 3.0,
            'position_qty': 0,
            'prices_df': None,
            'social_sentiment': -1.0,  # Minimum (très négatif)
            'social_summary': 'Extreme fear',
            'rsi': 10.0,  # Oversold
            'trend': 'DOWN',
            'decision': 'hold',
            'reasoning': 'Too much panic'
        }
        assert state['social_sentiment'] == -1.0
        assert state['rsi'] == 10.0
        assert state['trend'] == 'DOWN'
