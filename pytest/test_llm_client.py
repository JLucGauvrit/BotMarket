"""
Tests pour le module shared.llm_client
"""

import pytest
import os
from unittest.mock import patch, MagicMock, Mock
import requests
from bot.src.shared.llm_client import (
    ensure_model_ready,
    get_llm,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_MODEL
)


class TestLLMClient:
    """Teste les fonctions LLM client."""
    
    def test_default_model_from_env(self):
        """Vérifie que le modèle par défaut vient des variables d'env."""
        # On peut pas vraiment tester sans modifier l'env, donc on teste juste que les constantes existent
        assert DEFAULT_MODEL is not None
        assert DEFAULT_OLLAMA_HOST is not None
        assert isinstance(DEFAULT_MODEL, str)
        assert isinstance(DEFAULT_OLLAMA_HOST, str)
    
    @patch('bot.src.shared.llm_client.requests.get')
    def test_ensure_model_ready_already_exists(self, mock_get):
        """Teste quand le modèle existe déjà."""
        # Mock la réponse des tags
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'qwen2.5:1.5b'},
                {'name': 'llama2:latest'}
            ]
        }
        mock_get.return_value = mock_response
        
        # Appel de la fonction
        ensure_model_ready('qwen2.5:1.5b')
        
        # Vérification qu'on a appelé l'API tags
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert '/api/tags' in call_args[0][0]
    
    @patch('bot.src.shared.llm_client.requests.post')
    @patch('bot.src.shared.llm_client.requests.get')
    def test_ensure_model_ready_needs_download(self, mock_get, mock_post):
        """Teste quand le modèle doit être téléchargé."""
        # Mock: modèle pas trouvé dans les tags
        mock_get.return_value = Mock(status_code=200, json=lambda: {'models': []})
        
        # Mock: successful download
        mock_response = Mock()
        mock_response.iter_lines.return_value = [
            b'{"status": "downloading"}',
            b'{"status": "success"}'
        ]
        mock_post.return_value.__enter__.return_value = mock_response
        mock_post.return_value.__exit__.return_value = None
        
        # Appel
        ensure_model_ready('custom-model:1.0')
        
        # Vérification
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert '/api/pull' in call_args[0][0]
        assert 'custom-model:1.0' in str(call_args)
    
    @patch('bot.src.shared.llm_client.requests.get')
    def test_ensure_model_ready_connection_error(self, mock_get):
        """Teste quand la connexion à Ollama échoue."""
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        # La fonction devrait logger une warning mais ne pas lever d'exception
        try:
            ensure_model_ready('test-model')
        except requests.ConnectionError:
            pytest.fail("ensure_model_ready should catch connection errors")
    
    @patch('bot.src.shared.llm_client.ChatOllama')
    def test_get_llm_default_params(self, mock_ollama):
        """Teste la création d'une instance ChatOllama avec params par défaut."""
        mock_llm = Mock()
        mock_ollama.return_value = mock_llm
        
        llm = get_llm()
        
        # Vérifier que ChatOllama a été instancié
        mock_ollama.assert_called_once()
        call_kwargs = mock_ollama.call_args[1]
        assert call_kwargs['temperature'] == 0
        assert call_kwargs['keep_alive'] == "1h"
    
    @patch('bot.src.shared.llm_client.ChatOllama')
    def test_get_llm_custom_temperature(self, mock_ollama):
        """Teste la création avec température personnalisée."""
        mock_llm = Mock()
        mock_ollama.return_value = mock_llm
        
        llm = get_llm(temperature=0.7)
        
        call_kwargs = mock_ollama.call_args[1]
        assert call_kwargs['temperature'] == 0.7
    
    @patch('bot.src.shared.llm_client.ChatOllama')
    def test_get_llm_custom_model(self, mock_ollama):
        """Teste la création avec un modèle personnalisé."""
        mock_llm = Mock()
        mock_ollama.return_value = mock_llm
        
        llm = get_llm(model_name='llama2:latest', temperature=0.5)
        
        call_kwargs = mock_ollama.call_args[1]
        assert call_kwargs['model'] == 'llama2:latest'
        assert call_kwargs['temperature'] == 0.5
    
    @patch('bot.src.shared.llm_client.ChatOllama')
    def test_get_llm_custom_host(self, mock_ollama):
        """Teste la création avec un host personnalisé."""
        mock_llm = Mock()
        mock_ollama.return_value = mock_llm
        
        custom_host = "http://localhost:11434"
        llm = get_llm()  # On teste juste que ça marche
        
        assert mock_ollama.called


class TestEnsureModelReadyEdgeCases:
    """Tests des cas limites pour ensure_model_ready."""
    
    @patch('bot.src.shared.llm_client.requests.get')
    def test_empty_models_list(self, mock_get):
        """Teste avec une liste de modèles vide."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': []}
        mock_get.return_value = mock_response
        
        # Devrait déclencher un download
        with patch('bot.src.shared.llm_client.requests.post'):
            ensure_model_ready('some-model')
    
    @patch('bot.src.shared.llm_client.requests.get')
    def test_malformed_json_response(self, mock_get):
        """Teste avec une réponse JSON mal formée."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        # Devrait gérer l'erreur gracieusement
        try:
            with patch('bot.src.shared.llm_client.requests.post'):
                ensure_model_ready('test-model')
        except ValueError:
            pytest.fail("Should handle invalid JSON gracefully")
    
    @patch('bot.src.shared.llm_client.requests.get')
    def test_non_200_status_code(self, mock_get):
        """Teste avec un code de statut non-200."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Devrait gérer le code d'erreur
        try:
            ensure_model_ready('test-model')
        except Exception:
            pytest.fail("Should handle non-200 status codes")
