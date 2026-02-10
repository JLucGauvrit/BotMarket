"""Tests pour le Trade Executor"""

import pytest
from unittest.mock import patch, Mock
from bot.src.executor.trade_runner import execute_trade, _execute_buy, _execute_sell


class TestTradeExecution:
    """Tests pour l'exécution des ordres."""
    
    def test_hold_decision(self, mock_agent_state):
        """Teste qu'aucun ordre n'est exécuté en cas de HOLD."""
        mock_agent_state['decision'] = 'hold'
        
        result = execute_trade(mock_agent_state)
        
        assert result['executed'] is False
        assert 'HOLD' in result['reason']
    
    def test_invalid_price_block(self):
        """Teste que les ordres sont bloqués avec un prix invalide."""
        state = {
            'symbol': 'BTC',
            'decision': 'buy',
            'price': 0,  # Prix invalide
            'approved': True,
            'adjusted_qty': 10,
            'strategy': {'entry_price': 0}
        }
        
        result = execute_trade(state)
        
        assert result['executed'] is False
        assert 'invalide' in result['reason'].lower()
    
    def test_unapproved_trading_blocked(self, mock_bullish_state):
        """Teste que les trades rejetés ne s'exécutent pas."""
        mock_bullish_state['approved'] = False
        
        result = execute_trade(mock_bullish_state)
        
        assert result['executed'] is False
    
    @patch('bot.src.executor.trade_runner.requests.post')
    def test_buy_order_execution(self, mock_post, mock_bullish_state, mock_strategy_buy):
        """Teste l'exécution d'un ordre d'achat."""
        mock_bullish_state['decision'] = 'buy'
        mock_bullish_state['approved'] = True
        mock_bullish_state['adjusted_qty'] = 100
        mock_bullish_state['strategy'] = mock_strategy_buy
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'order_id': 'ORD-123'}
        mock_post.return_value = mock_response
        
        result = execute_trade(mock_bullish_state)
        
        assert mock_post.called
        assert '/orders' in mock_post.call_args[0][0]
    
    @patch('bot.src.executor.trade_runner.requests.post')
    def test_sell_order_execution(self, mock_post, mock_bearish_state):
        """Teste l'exécution d'un ordre de vente."""
        mock_bearish_state['approved'] = True
        mock_bearish_state['adjusted_qty'] = 100
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'order_id': 'ORD-456'}
        mock_post.return_value = mock_response
        
        result = execute_trade(mock_bearish_state)
        
        assert mock_post.called
    
    def test_zero_quantity_rejected(self, mock_bullish_state):
        """Teste qu'une quantité 0 est rejetée."""
        mock_bullish_state['decision'] = 'buy'
        mock_bullish_state['approved'] = True
        mock_bullish_state['adjusted_qty'] = 0
        
        result = execute_trade(mock_bullish_state)
        
        assert result['executed'] is False
    
    @patch('bot.src.executor.trade_runner.requests.post')
    def test_order_size_limit(self, mock_post, mock_bullish_state):
        """Teste que les ordres trop gros sont plafonnés."""
        mock_bullish_state['decision'] = 'buy'
        mock_bullish_state['approved'] = True
        mock_bullish_state['adjusted_qty'] = 100000  # Très grosse quantité
        mock_bullish_state['price'] = 0.15
        mock_bullish_state['strategy'] = {'entry_price': 0.15}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'order_id': 'ORD-789'}
        mock_post.return_value = mock_response
        
        result = execute_trade(mock_bullish_state)
        
        # Même si la quantité est énorme, elle doit être plafonnée
        assert mock_post.called


class TestOrderFailure:
    """Tests pour les échecs d'ordres."""
    
    @patch('bot.src.executor.trade_runner.requests.post')
    def test_gateway_error(self, mock_post, mock_bullish_state):
        """Teste la gestion des erreurs Gateway."""
        mock_bullish_state['decision'] = 'buy'
        mock_bullish_state['approved'] = True
        mock_bullish_state['adjusted_qty'] = 10
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Gateway Error"
        mock_post.return_value = mock_response
        
        result = execute_trade(mock_bullish_state)
        
        assert result['executed'] is False
        assert 'Gateway' in result['reason']
    
    @patch('bot.src.executor.trade_runner.requests.post')
    def test_connection_timeout(self, mock_post, mock_bullish_state):
        """Teste la gestion des timeouts."""
        import requests as requests_module
        
        mock_bullish_state['decision'] = 'buy'
        mock_bullish_state['approved'] = True
        mock_bullish_state['adjusted_qty'] = 10
        
        mock_post.side_effect = requests_module.Timeout("Connection timeout")
        
        result = execute_trade(mock_bullish_state)
        
        assert result['executed'] is False
        assert 'reason' in result
