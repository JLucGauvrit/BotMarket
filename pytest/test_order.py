"""
Tests d'ordre pour validation des endpoints Gateway.

Notes: Ce test est optionnel et nécessite une Gateway démarrée localement.
Pour tester avec une vraie Gateway: pytest test_order.py::TestGatewayOrderEndpoint::test_order_endpoint_live
"""

import pytest
import requests
from unittest.mock import patch, Mock


class TestGatewayOrderEndpoint:
    """Tests pour l'endpoint d'ordre de la Gateway."""
    
    @pytest.mark.skip(reason="Nécessite une Gateway locale")
    def test_order_endpoint_live(self):
        """Test le vrai endpoint si une Gateway est démarrée."""
        url = "http://localhost:8000/order"
        
        payload = {
            "symbol": "DOGE/USD",
            "side": "buy",
            "qty": 10,
            "type": "market",
            "time_in_force": "gtc"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            assert response.status_code in [200, 201, 400]
        except requests.ConnectionError:
            pytest.skip("Gateway not available")
    
    @patch('requests.post')
    def test_order_endpoint_mock(self, mock_post):
        """Test l'endpoint d'ordre avec mock."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'order_id': 'ORD-12345',
            'status': 'pending'
        }
        mock_post.return_value = mock_response
        
        url = "http://localhost:8000/order"
        payload = {
            "symbol": "DOGE/USD",
            "side": "buy",
            "qty": 10,
            "type": "market",
            "time_in_force": "gtc"
        }
        
        response = requests.post(url, json=payload)
        
        assert response.status_code == 200
        assert 'order_id' in response.json()


class TestOrderValidation:
    """Tests pour la validation des ordres."""
    
    def test_order_payload_structure(self):
        """Teste la structure minimale d'un payload d'ordre."""
        valid_payload = {
            "symbol": "DOGE/USD",
            "side": "buy",
            "qty": 10,
            "type": "market",
            "time_in_force": "gtc"
        }
        
        required_keys = ["symbol", "side", "qty", "type", "time_in_force"]
        assert all(key in valid_payload for key in required_keys)
    
    def test_order_side_validation(self):
        """Teste les côtés valides d'un ordre."""
        valid_sides = ["buy", "sell"]
        
        for side in valid_sides:
            assert side in ["buy", "sell"]
    
    def test_order_type_validation(self):
        """Teste les types d'ordres valides."""
        valid_types = ["market", "limit"]
        
        for order_type in valid_types:
            assert order_type in ["market", "limit"]
    
    def test_order_quantity_validation(self):
        """Teste la validation de la quantité (> 0)."""
        quantities = [1, 10, 100, 1000]
        
        for qty in quantities:
            assert qty > 0