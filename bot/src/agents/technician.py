import random
from ..shared.state import AgentState

# Note: Pour faire du vrai RSI, il faudrait un historique de prix (OHLCV).
# Comme la Gateway actuelle ne le fournit pas encore, on simule une logique 
# ou on implémente un calcul simple si on stocke l'historique en local.

def calculate_indicators(state: AgentState):
    print(f"📈 [Technician] Calcul des indicateurs...")
    
    # Simulation intelligente pour le test
    # Dans le futur: appel à pandas_ta avec des données historiques
    
    # Si le sentiment social est très haut, on simule un RSI haut (surachat)
    # pour voir si l'analyste arrive à arbitrer.
    simulated_rsi = 50.0
    
    trend = "neutral"
    if state['price'] > 155: # Exemple simple
        simulated_rsi = 75
        trend = "bullish"
    elif state['price'] < 145:
        simulated_rsi = 25
        trend = "bearish"
        
    return {
        "rsi": simulated_rsi, 
        "trend": trend
    }