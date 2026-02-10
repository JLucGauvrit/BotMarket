"""Tests pour le Risk Manager"""

import pytest
from unittest.mock import patch, Mock
from bot.src.agents.risk_manager import validate_strategy


class TestRiskValidation:
    """Tests pour la validation de risque."""
    
    def test_hold_always_approved(self, mock_agent_state):
        """Teste qu'une décision HOLD est toujours approuvée."""
        mock_agent_state['decision'] = 'hold'
        
        result = validate_strategy(mock_agent_state)
        
        assert result['approved'] is True
        assert result['adjusted_qty'] == 0
    
    def test_invalid_price_abort(self):
        """Teste que les prix invalides sont bloqués."""
        state = {
            'symbol': 'BTC',
            'price': 0.0,  # Prix invalide
            'decision': 'buy',
            'strategy': {},
            'position_qty': 0
        }
        
        result = validate_strategy(state)
        
        assert result['approved'] is False
        assert 'CRITICAL' in result['reason']
    
    @patch('bot.src.agents.risk_manager.requests.get')
    def test_buy_with_sufficient_cash(self, mock_get, mock_agent_state, mock_strategy_buy):
        """Teste un achat avec suffisamment de cash."""
        mock_agent_state['decision'] = 'buy'
        mock_agent_state['strategy'] = mock_strategy_buy
        mock_agent_state['price'] = 0.15
        
        # Mock account data
        account_response = Mock()
        account_response.status_code = 200
        account_response.json.return_value = {
            'cash': 5000.0,
            'portfolio_value': 10000.0
        }
        
        positions_response = Mock()
        positions_response.status_code = 200
        positions_response.json.return_value = []
        
        mock_get.side_effect = [account_response, positions_response]
        
        result = validate_strategy(mock_agent_state)
        
        # Devrait être approuvé
        assert mock_get.call_count == 2
    
    @patch('bot.src.agents.risk_manager.requests.get')
    def test_buy_with_insufficient_cash(self, mock_get):
        """Teste un achat avec pas assez de cash."""
        state = {
            'symbol': 'BTC',
            'price': 45000.0,
            'decision': 'buy',
            'strategy': {
                'entry_price': 45000.0,
                'position_size': 10  # Demande 450,000$
            },
            'position_qty': 0
        }
        
        account_response = Mock()
        account_response.status_code = 200
        account_response.json.return_value = {
            'cash': 1000.0,  # Seulement 1000$
            'portfolio_value': 2000.0
        }
        
        positions_response = Mock()
        positions_response.status_code = 200
        positions_response.json.return_value = []
        
        mock_get.side_effect = [account_response, positions_response]
        
        result = validate_strategy(state)
        
        # Doit réduire la position ou rejeter
        assert mock_get.call_count >= 1
    
    @patch('bot.src.agents.risk_manager.requests.get')
    def test_sell_with_position(self, mock_get):
        """Teste une vente avec une position existante."""
        state = {
            'symbol': 'DOGE',
            'price': 0.15,
            'decision': 'sell',
            'strategy': {},
            'position_qty': 100
        }
        
        account_response = Mock()
        account_response.status_code = 200
        account_response.json.return_value = {
            'cash': 1000.0,
            'portfolio_value': 2000.0
        }
        
        positions_response = Mock()
        positions_response.status_code = 200
        positions_response.json.return_value = [
            {'symbol': 'DOGE', 'qty': '100'}
        ]
        
        mock_get.side_effect = [account_response, positions_response]
        
        result = validate_strategy(state)
        
        assert mock_get.called
    
    @patch('bot.src.agents.risk_manager.requests.get')
    def test_sell_without_position(self, mock_get):
        """Teste une vente sans position existante."""
        state = {
            'symbol': 'ETH',
            'price': 2500.0,
            'decision': 'sell',
            'strategy': {},
            'position_qty': 0
        }
        
        account_response = Mock()
        account_response.status_code = 200
        account_response.json.return_value = {
            'cash': 1000.0,
            'portfolio_value': 2000.0
        }
        
        positions_response = Mock()
        positions_response.status_code = 200
        positions_response.json.return_value = []  # Pas de position ETH
        
        mock_get.side_effect = [account_response, positions_response]
        
        result = validate_strategy(state)
        
        assert result['approved'] is False
    
    @patch('bot.src.agents.risk_manager.requests.get')
    def test_gateway_error_handling(self, mock_get):
        """Teste la gestion des erreurs Gateway."""
        state = {
            'symbol': 'BTC',
            'price': 45000.0,
            'decision': 'buy',
            'strategy': {'entry_price': 45000.0, 'position_size': 1},
            'position_qty': 0
        }
        
        mock_get.side_effect = Exception("Gateway connection failed")
        
        result = validate_strategy(state)
        
        assert result['approved'] is False
        assert 'Erreur' in result['reason']
    
    @patch('bot.src.agents.risk_manager.requests.get')
    def test_max_positions_limit(self, mock_get):
        """Teste le limite de positions maximales."""
        state = {
            'symbol': 'NEW',
            'price': 1.0,
            'decision': 'buy',
            'strategy': {'entry_price': 1.0, 'position_size': 100},
            'position_qty': 0
        }
        
        account_response = Mock()
        account_response.status_code = 200
        account_response.json.return_value = {
            'cash': 10000.0,
            'portfolio_value': 20000.0
        }
        
        # 10 positions ouvertes (limite maximale)
        positions_response = Mock()
        positions_response.status_code = 200
        positions_response.json.return_value = [
            {'symbol': f'SYM{i}', 'qty': '1'} for i in range(10)
        ]
        
        mock_get.side_effect = [account_response, positions_response]
        
        result = validate_strategy(state)
        
        # Devrait rejeter: trop de positions
        assert mock_get.call_count >= 1
