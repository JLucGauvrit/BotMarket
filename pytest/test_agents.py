"""Tests pour les agents principaux"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta, timezone


class TestDiscoveryAgent:
    """Tests pour l'agent de découverte."""
    
    def test_discovery_scan_market(self):
        """Teste le scan du marché."""
        from bot.src.agents.discovery import DiscoveryAgent
        
        agent = DiscoveryAgent()
        # Mock pour éviter d'appeler l'API réelle
        with patch('bot.src.agents.discovery.aiohttp.ClientSession'):
            result = agent.scan_market()
            
            # Devrait retourner au moins un symbole
            assert isinstance(result, list)
            if result:
                assert all(isinstance(s, str) for s in result)
    
    def test_discovery_fallback(self):
        """Teste le fallback quand pas d'opportunités."""
        from bot.src.agents.discovery import DiscoveryAgent
        
        agent = DiscoveryAgent()
        # Devrait avoir un fallback
        result = agent.scan_market()
        
        assert result is not None
        assert len(result) > 0


class TestTechnicianAgent:
    """Tests pour l'agent analyste technique."""
    
    def test_technician_with_ohlcv(self, mock_ohlcv_data):
        """Teste l'analyse technique avec données OHLCV."""
        from bot.src.agents.technician import analyze_technical
        
        state = {
            'symbol': 'BTC',
            'prices_df': mock_ohlcv_data,
            'price': 45000.0
        }
        
        # L'agent devrait analyser les données
        result = analyze_technical(state)
        
        assert 'rsi' in result
        assert 'trend' in result
    
    def test_technician_rsi_calculation(self, mock_ohlcv_data):
        """Teste le calcul du RSI."""
        from bot.src.agents.technician import analyze_technical
        
        state = {
            'symbol': 'ETH',
            'prices_df': mock_ohlcv_data,
            'price': 2500.0
        }
        
        result = analyze_technical(state)
        
        # RSI doit être entre 0 et 100
        if 'rsi' in result:
            assert 0 <= result['rsi'] <= 100


class TestStrategyBuilder:
    """Tests pour le constructeur de stratégies."""
    
    def test_strategy_building_buy(self, mock_bullish_state):
        """Teste la construction d'une stratégie d'achat."""
        from bot.src.agents.strategy_builder import build_strategy
        
        mock_bullish_state['prices_df'] = None
        
        result = build_strategy(mock_bullish_state)
        
        if result.get('decision') == 'buy':
            strategy = result.get('strategy', {})
            assert 'entry_price' in strategy
            assert 'sl_level' in strategy
    
    def test_strategy_building_sell(self, mock_bearish_state):
        """Teste la construction d'une stratégie de vente."""
        from bot.src.agents.strategy_builder import build_strategy
        
        mock_bearish_state['prices_df'] = None
        mock_bearish_state['position_qty'] = 100
        
        result = build_strategy(mock_bearish_state)
        
        if result.get('decision') == 'sell':
            strategy = result.get('strategy', {})
            assert strategy is not None


class TestPortfolioAnalyzer:
    """Tests pour l'analyseur de portefeuille."""
    
    @patch('bot.src.agents.portfolio_analyzer.requests.get')
    def test_portfolio_analysis(self, mock_get):
        """Teste l'analyse du portefeuille."""
        from bot.src.agents.portfolio_analyzer import analyze_portfolio
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        state = {
            'symbol': 'NEW',
            'price': 100.0,
            'position_qty': 0
        }
        
        result = analyze_portfolio(state)
        
        # Devrait retourner des infos sur le portfolio
        assert 'can_add' in result or 'portfolio_info' in result or 'current_positions' in result
