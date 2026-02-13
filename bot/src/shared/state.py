from typing import TypedDict, List, Literal, Optional, Any


"""
Types utilitaires pour l'état partagé des agents (`AgentState`).

`AgentState` est la structure de données transmise entre les noeuds du graphe
LangGraph. Elle contient à la fois des informations de marché (prix, historisation),
des métriques d'analyse (RSI, tendance), et la décision finale proposée par les
composants de décision.

Args:
symbol (str): Symbole de l'actif (ex: 'BTC', 'AAPL').
price (float): Prix courant de l'actif. Utilisé pour le sizing et les vérifications de sécurité.
position_qty (int): Quantité actuellement détenue en portefeuille.
prices_df (Any): Historique des prix (généralement un `pandas.DataFrame`) utilisé par l'agent technique.
social_sentiment (float): Score agrégé de sentiment social (ex: -1.0..1.0).
social_summary (str): Résumé textuel du sentiment (ex: 'bullish', 'bearish', 'neutral').
rsi (float): RSI calculé pour l'actif (0-100).
trend (str): Indication de tendance (ex: 'up', 'down', 'sideways', 'unknown').
decision (Literal['buy','sell','hold']): Décision finale proposée par le pipeline.
reasoning (str): Motifs ou logiques expliquant la décision (utilisé pour audit et debugging).

Notes:
- Cette structure est utilisée par `StateGraph(AgentState)` et doit rester serialisable
    par JSON lorsque nécessaire (ex: logs, persistance temporaire).
"""


class AgentState(TypedDict):
        """TypedDict décrivant l'`AgentState` transmis entre agents.

        Les clés ci-dessous sont attendues par de nombreux agents du pipeline.
        """

        symbol: str
        price: float
        position_qty: int

        # Ajout critique pour le Technicien
        prices_df: Any  # pandas.DataFrame

        social_sentiment: float
        social_summary: str

        # Analyse Technique
        rsi: float
        trend: str

        # Décision Finale
        decision: Literal["buy", "sell", "hold"]
        reasoning: str
    