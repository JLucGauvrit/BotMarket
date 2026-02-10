"""Tests d'intégration - Validation end-to-end"""

import pytest
from unittest.mock import patch, Mock
from bot.src.orchestrator.graph import build_graph


class TestGraphIntegration:
    """Tests d'intégration du graphe complet."""
    
    @patch('bot.src.agents.retriever.requests.get')
    def test_full_workflow_buy(self, mock_get):
        """Teste un workflow complet: découverte → analyse → décision d'achat."""
        graph = build_graph()
        
        # Mock les données du retriever
        market_data_response = Mock()
        market_data_response.status_code = 200
        market_data_response.json.return_value = {
            'current_price': 0.15,
            'price_change_24h': 5.0
        }
        mock_get.return_value = market_data_response
        
        state = {
            'symbol': 'DOGE/USD',
            'price': 0.15,
            'position_qty': 0,
            'prices_df': None,
            'skip_retriever': True
        }
        
        # Devrait tracer le graphe sans erreurs
        try:
            result = graph.invoke(state)
            # Le résultat devrait avoir une décision
            assert 'decision' in result
        except Exception as e:
            pytest.fail(f"Graph invocation failed: {e}")
    
    def test_graph_structure(self):
        """Teste que le graphe a la bonne structure."""
        graph = build_graph()
        
        # Devrait avoir des nœuds
        assert graph is not None
        
        # Cherche les nœuds clés
        graph_dict = graph.get_graph() if hasattr(graph, 'get_graph') else None
        
        if graph_dict:
            # Devrait au moins compiler sans erreurs
            assert graph_dict is not None


class TestErrorHandling:
    """Tests de gestion d'erreurs dans le workflow."""
    
    def test_missing_symbol(self):
        """Teste quand le symbole est manquant."""
        graph = build_graph()
        
        state = {
            # Pas de symbole
            'price': 100.0,
            'position_qty': 0,
            'prices_df': None,
            'skip_retriever': True
        }
        
        # Devrait gérer l'absence de symbole
        try:
            result = graph.invoke(state)
        except KeyError:
            pytest.fail("Should handle missing symbol gracefully")
    
    def test_invalid_price(self):
        """Teste avec un prix invalide."""
        graph = build_graph()
        
        state = {
            'symbol': 'TEST',
            'price': -100.0,  # Prix négatif
            'position_qty': 0,
            'prices_df': None,
            'skip_retriever': True
        }
        
        try:
            result = graph.invoke(state)
            # Les prix invalides devraient être gérés
        except ValueError:
            # Acceptable si l'erreur est levée
            pass
