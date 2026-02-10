# Tests Pytest du Bot Market

Guide d'organisation et d'exécution des tests.

## Structure des tests

```
pytest/
├── conftest.py              # Fixtures Pytest communes
├── pytest.ini               # Configuration pytest
├── test_state.py            # Tests du state (AgentState)
├── test_llm_client.py       # Tests du client LLM
├── test_trade_executor.py   # Tests de l'exécuteur d'ordres
├── test_risk_manager.py     # Tests du gestionnaire de risquez
├── test_agents.py           # Tests des agents (technician, discovery, etc.)
├── test_integration.py      # Tests d'intégration du graphe
└── README.md                # Ce fichier
```

## Catégories de tests

### 1. **test_state.py**
Tests des structures de données et de l'état.
- Création d'AgentState
- Validations des valeurs extremes
- Accès aux données

### 2. **test_llm_client.py**
Tests du client LLM et de la communication Ollama.
- Vérification de la disponibilité des modèles
- Téléchargement automatique des modèles
- Gestion des erreurs de connexion
- Factory pour ChatOllama

### 3. **test_trade_executor.py**
Tests de l'exécution des ordres.
- Validation des ordres d'achat/vente
- Gestion des prix invalides
- Rejets de trading sans approbation
- Timeouts et erreurs Gateway
- Plafonnement des ordres trop gros

### 4. **test_risk_manager.py**
Tests de validation des risques.
- Approbation des ordres HOLD
- Blocage des prix invalides
- Validation du cash disponible
- Limites de positions
- Gestion des positions existantes
- Isolation des risques

### 5. **test_agents.py**
Tests unitaires des agents individuels.
- Agent de découverte (Discovery)
- Agent analyste technique (Technician)
- Constructeur de stratégies (Strategy Builder)
- Analyseur de portefeuille (Portfolio Analyzer)

### 6. **test_integration.py**
Tests d'intégration du graphe complet.
- Workflow end-to-end
- Structure du graphe
- Gestion des erreurs globales

### 7. **conftest.py**
Fixtures Pytest réutilisables:
- `mock_agent_state`: État neutre standard
- `mock_bullish_state`: État haussier
- `mock_bearish_state`: État baissier
- `mock_strategy_buy`: Stratégie d'achat
- `mock_strategy_sell`: Stratégie de vente
- `mock_account_data`: Données de compte
- `mock_positions`: Positions ouvertes
- `mock_ohlcv_data`: Données techniques (OHLCV)
- `mock_gateway_responses`: Réponses Gateway mockées

## Exécution des tests

### Tous les tests
```bash
cd pytest
pytest -v
```

### Tests spécifiques
```bash
# Tests du state uniquement
pytest test_state.py -v

# Tests du risk manager
pytest test_risk_manager.py -v

# Tests avec couverture
pytest --cov=bot --cov-report=html
```

### Tests par marqueur
```bash
# Tests unitaires seulement
pytest -m unit -v

# Tests d'intégration
pytest -m integration -v
```

### Tests d'un fichier spécifique
```bash
pytest test_trade_executor.py::TestTradeExecution::test_hold_decision -v
```

## Conventions

- **Classes de test**: `Test*` (ex: `TestTradeExecution`)
- **Méthodes de test**: `test_*` (ex: `test_hold_decision`)
- **Fixtures**: `mock_*` ou `@pytest.fixture`
- **Mocks**: Utiliser `unittest.mock.patch` et `Mock()`

## Couverture de code

Target: **> 80% de couverture**

```bash
pytest --cov=bot --cov-report=term-missing
```

## Notes d'exécution

1. **Aucune dépendance externe requise** - Tous les appels Gateway sont mockés
2. **Tests rapides** - < 1 sec par test
3. **Pas de données en direct** - Tests isolés de l'API réelle
4. **Déterministes** - Résultats identiques à chaque exécution

## Ajout de nouveaux tests

Template:
```python
def test_new_feature(self, mock_agent_state):
    \"\"\"Brève description du test.\"\"\"
    # Arrange
    mock_agent_state['symbol'] = 'TEST'
    
    # Act
    result = function_under_test(mock_agent_state)
    
    # Assert
    assert result['expected_key'] == expected_value
```

## Debugging

### Afficher les logs
```bash
pytest test_file.py -v -s
```

### Mode verbose
```bash
pytest -vv --tb=long
```

### PDB au premier failure
```bash
pytest --pdb
```

## CI/CD Integration

Pour l'intégration GitHub Actions, ajoutez:
```yaml
- name: Run pytest
  run: |
    cd pytest
    pytest --cov=bot --junitxml=test-results.xml
```
