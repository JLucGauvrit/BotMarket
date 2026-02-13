# 🤖 AI Trading Bot - Alpaca x LangGraph

Ce projet est un bot de trading algorithmique piloté par une architecture multi-agents (IA) locale. Il utilise le **Paper Trading** pour valider des stratégies "Hunter" (recherche de pépites) sans risque financier.

## 🏗️ Architecture du Projet

Le système est entièrement conteneurisé et s'articule autour de quatre piliers :

* **Brain (LangGraph)** : Orchestration asynchrone des décisions via un graphe d'agents cyclique composé de 8 agents (Discovery, Fundamental, Technician, Sentiment, Regime, Portfolio, Strategy, Risk Validator).
* **Gateway (FastAPI)** : Pont sécurisé isolant le SDK Alpaca-py pour gérer l'exécution réelle des ordres au marché et la récupération des données de compte.
* **LLM (Ollama)** : Analyse de sentiment multi-source et aide décisionnelle tournant 100% localement via `ChatOllama`.
* **Observability (Streamlit)** : Dashboard web réactif pour monitorer la valeur totale du portfolio, l'historique des ordres et les positions actives en temps réel.

## 🏹 Stratégie "Hunter" & Diversité

Le bot utilise un mode **Hybride** pour maximiser les opportunités de marché :

* **Crypto Trending** : Scan automatique des tokens les plus recherchés ("Trending") via l'API CoinGecko.
* **High Volatility Stocks** : Injection systématique d'actions "Spicy" à fort beta (MSTR, COIN, PLTR, AMD, etc.) pour une exposition tech agressive.
* **Sentiment Timeseries** : Analyse de la tendance du sentiment social (Twitter/Reddit) sur 7 à 14 jours avec calcul de conviction par le LLM.

## 🚀 Démarrage Rapide

### 1. Configuration

Créez un fichier `.env` à la racine (assure-toi qu'il est listé dans ton `.dockerignore`) :

```env
ALPACA_API_KEY=votre_cle_paper_ici
ALPACA_SECRET_KEY=votre_secret_ici
ALPACA_PAPER=True
OLLAMA_HOST=http://ollama:11434
MODEL=qwen2.5:1.5b

```

### 2. Lancement

```bash
# Construire et lancer l'infrastructure complète
docker-compose up -d --build

# Le modèle LLM est téléchargé automatiquement au premier démarrage via llm_client.py

```

### 3. Exécution des Tests

Le projet inclut une suite de tests unitaires et d'intégration utilisant des mocks (aucune dépendance externe requise) :

```bash
cd pytest
pytest -v

```

## 🛡️ Sécurité & Optimisation

Le projet suit les recommandations **Docker Scout** pour garantir une infrastructure saine :

* **Images légères** : Utilisation de `python:3.11-slim` pour réduire la surface d'attaque et le poids des conteneurs.
* **Scan CVE** : Zéro vulnérabilité critique détectée sur l'image `brain`.
* **Isolation Réseau** : Communication inter-services restreinte via le réseau interne `trading-net`.

## 🛠️ Roadmap Actualisée

* [x] **Discovery V3** : Mix hybride Crypto Trending / Spicy Stocks.
* [x] **Risk Management** : Validation d'exposition dynamique (max 20% par ligne).
* [x] **OHLC Crypto** : Récupération des bougies historiques sur CoinGecko pour analyse technique.
* [ ] Implémentation du mode Short (Vente à découvert).
* [ ] Système de stop-loss suiveur (Trailing Stop) géré par la Gateway.
* [ ] Alertes Discord/Telegram sur exécution d'ordre.
