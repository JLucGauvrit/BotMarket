# 🤖 AI Trading Bot - Alpaca x LangGraph

Projet de bot de trading algorithmique piloté par une architecture multi-agents (IA) locale. Il utilise le **Paper Trading** pour valider des stratégies "Hunter" (recherche de pépites) sans risque financier.

## 🏗️ Architecture du Projet

Le projet est entièrement conteneurisé et s'articule autour de quatre piliers :

* **Brain (LangGraph)** : Orchestration des décisions via un graphe d'agents cyclique (Discovery, Technician, Risk, Executor).
* **Gateway (FastAPI)** : Pont sécurisé isolant les clés API Alpaca et gérant l'exécution des ordres.
* **LLM (Ollama)** : Analyse de sentiment et décisionnel technique tournant 100% en local via `ChatOllama`.
* **Observability (Streamlit)** : Dashboard web pour monitorer le portfolio et les logs des agents en temps réel.


## 🚀 Démarrage Rapide

### 1. Configuration

Crée un fichier `.env` à la racine (assure-toi qu'il est listé dans ton `.dockerignore`) :

```env
ALPACA_API_KEY=votre_cle_paper_ici
ALPACA_SECRET_KEY=votre_secret_ici
ALPACA_PAPER=True
OLLAMA_HOST=http://ollama:11434
MODEL=qwen2.5:1.5b

```

### 2. Lancement

```bash
# Construire et lancer l'infrastructure
docker-compose up -d --build

# Le modèle est téléchargé automatiquement au premier lancement via llm_client.py

```

### 3. Exécution des Tests

Le projet inclut une suite de tests unitaires et d'intégration mockés (pas besoin de connexion API pour tester) :

```bash
cd pytest
pytest -v

```

## 🛡️ Sécurité & Optimisation

Le projet suit les recommandations **Docker Scout** pour garantir une infrastructure saine :

* **Images de base** : Utilisation de `python:3.11-slim` pour réduire la taille et les vulnérabilités.
* **Scan CVE** : Zéro vulnérabilité critique détectée sur l'image `brain`.
* **Isolation** : Réseau interne `trading-net` pour les communications entre agents et gateway.

## 🛠️ Roadmap Actualisée

* [x] **Discovery V3** : Mix hybride Crypto Trending / Spicy Stocks.
* [x] **Risk Management** : Validation d'exposition dynamique (max 20% par ligne).
* [x] **OHLC Crypto** : Récupération des bougies historiques sur CoinGecko pour analyse technique.
* [ ] Implémentation du mode Short (Vente à découvert).
* [ ] Système de stop-loss suiveur (Trailing Stop) géré par la Gateway.
* [ ] Alertes Discord sur exécution d'ordre.
