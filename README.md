# 🤖 AI Trading Bot - Alpaca x LangGraph

Projet de bot de trading algorithmique piloté par une architecture d'agents (IA) locale, utilisant le Paper Trading pour tester des stratégies sans risque financier.

## 🏗️ Architecture du Projet

Le projet est entièrement conteneurisé et s'articule autour de quatre piliers :

* **Brain (LangGraph)** : Orchestration des décisions via un graphe d'agents cyclique.
* **LLM (Ollama)** : Analyse de sentiment et décisionnel technique tournant en local.
* **Execution (Alpaca-py)** : Interface avec l'API Alpaca pour le trading simulé d'actions US.
* **Observability (Streamlit)** : Dashboard web pour monitorer le portfolio et les logs des agents en temps réel.

## 🚀 Démarrage Rapide

### 1. Prérequis

* Docker & Docker Compose.
* Un compte [Alpaca Markets](https://alpaca.markets/) (clés API Paper Trading).

### 2. Configuration

Crée un fichier `.env` à la racine :

```env
ALPACA_API_KEY=votre_cle_ici
ALPACA_SECRET_KEY=votre_secret_ici
OLLAMA_HOST=http://ollama:11434

```

### 3. Lancement

```bash
# Lancer les services
docker-compose up -d

# Télécharger le modèle IA (ex: Llama3)
docker exec -it ollama ollama pull llama3

```

## 📊 Services & Accès

* **Bot Engine** : S'exécute en arrière-plan.
* **Ollama API** : `http://localhost:11434`
* **Dashboard Web** : `http://localhost:8501`

## 🛠️ Roadmap

* [ ] Implémentation du graphe de décision de base (Scan -> Analyse -> Exécution).
* [ ] Intégration de `pandas_ta` pour les indicateurs techniques.
* [ ] Système de logging persistant dans SQLite pour l'historique des décisions.
* [ ] Alertes Discord/Telegram sur exécution d'ordre.
