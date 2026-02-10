"""
Configuration pytest et fixtures communes.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta, timezone

# Ajouter le répertoire parent au sys.path pour les imports de bot
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.src.shared.state import AgentState


@pytest.fixture
def mock_agent_state():
    """Fixture: AgentState de base pour les tests."""
    return {
        'symbol': 'BTC/USD',
        'price': 45000.0,
        'position_qty': 0,
        'prices_df': None,
        'social_sentiment': 0.5,
        'social_summary': 'Mixed sentiment',
        'rsi': 50.0,
        'trend': 'NEUTRAL',
        'decision': 'hold',
        'reasoning': 'Waiting for signals'
    }


@pytest.fixture
def mock_bullish_state():
    """Fixture: AgentState avec signaux haussiers."""
    return {
        'symbol': 'DOGE/USD',
        'price': 0.15,
        'position_qty': 0,
        'prices_df': None,
        'social_sentiment': 0.8,
        'social_summary': 'Strongly bullish',
        'rsi': 30.0,
        'trend': 'UP',
        'decision': 'buy',
        'reasoning': 'Strong oversold reversal signal'
    }


@pytest.fixture
def mock_bearish_state():
    """Fixture: AgentState avec signaux baissiers."""
    return {
        'symbol': 'SHIB/USD',
        'price': 0.000008,
        'position_qty': 1000,
        'prices_df': None,
        'social_sentiment': -0.7,
        'social_summary': 'Strongly bearish',
        'rsi': 75.0,
        'trend': 'DOWN',
        'decision': 'sell',
        'reasoning': 'Overbought with negative sentiment'
    }


@pytest.fixture
def mock_strategy_buy():
    """Fixture: Stratégie d'achat standard."""
    return {
        'action': 'buy',
        'entry_price': 0.15,
        'position_size': 100,
        'sl_level': 0.14,
        'tp_targets': [
            {'level': 0.158, 'pct': 30},
            {'level': 0.165, 'pct': 40}
        ],
        'risk_reward': 1.8
    }


@pytest.fixture
def mock_strategy_sell():
    """Fixture: Stratégie de vente standard."""
    return {
        'action': 'sell',
        'exit_price': 0.000008,
        'qty': 1000,
        'reason': 'Overbought + negative sentiment',
        'pnl_pct': -20.0
    }


@pytest.fixture
def mock_account_data():
    """Fixture: Données de compte."""
    return {
        'cash': 5000.0,
        'portfolio_value': 10000.0,
        'total_equity': 15000.0,
        'buying_power': 5000.0
    }


@pytest.fixture
def mock_positions():
    """Fixture: Positions ouvertes."""
    return [
        {'symbol': 'BTC/USD', 'qty': 0.5, 'avg_price': 40000},
        {'symbol': 'ETH/USD', 'qty': 5, 'avg_price': 2000}
    ]


@pytest.fixture
def mock_ohlcv_data():
    """Fixture: Données OHLCV pour tests techniques."""
    import pandas as pd
    import numpy as np

    n = 100
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=n, freq='1D')
    
    base_price = 45000.0
    close = pd.Series(
        base_price + np.random.normal(0, base_price * 0.01, n),
        index=dates
    )
    
    df = pd.DataFrame({
        'Open': close * (1 + np.random.normal(0, 0.001, n)),
        'High': close * (1 + abs(np.random.normal(0, 0.005, n))),
        'Low': close * (1 - abs(np.random.normal(0, 0.005, n))),
        'Close': close,
        'Volume': np.random.randint(1000, 10000, n)
    }, index=dates)
    
    return df


@pytest.fixture
def mock_gateway_responses(monkeypatch):
    """Fixture: Mock des réponses Gateway."""
    
    def mock_get(url, *args, **kwargs):
        from unittest.mock import Mock
        response = Mock()
        
        if '/account' in url:
            response.status_code = 200
            response.json.return_value = {
                'cash': 5000.0,
                'portfolio_value': 10000.0
            }
        elif '/positions' in url:
            response.status_code = 200
            response.json.return_value = []
        else:
            response.status_code = 404
        
        return response
    
    return mock_get
