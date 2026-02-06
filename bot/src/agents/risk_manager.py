from ..shared.state import AgentState

MAX_POSITION_SIZE = 10 # On ne veut pas plus de 10 actions pour le test

def validate_risk(state: AgentState):
    decision = state['decision']
    qty = state['position_qty']
    cash = state.get('cash', 0.0)
    price = state['price']
    
    final_decision = decision
    
    # Règle 1: Ne pas acheter si on a déjà atteint la limite
    if decision == "buy" and qty >= MAX_POSITION_SIZE:
        print("🛡️ [Risk] Refus d'achat : Max position atteinte.")
        final_decision = "hold"
        
    # Règle 2: Ne pas acheter si pas assez de cash
    if decision == "buy" and cash < price:
        print("🛡️ [Risk] Refus d'achat : Fonds insuffisants.")
        final_decision = "hold"
        
    # Règle 3: Ne pas vendre si on n'a rien
    if decision == "sell" and qty <= 0:
        print("🛡️ [Risk] Refus de vente : Pas de position.")
        final_decision = "hold"

    return {"decision": final_decision}
