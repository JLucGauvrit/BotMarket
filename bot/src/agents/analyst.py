from ..shared.state import AgentState
from ..shared.llm_client import get_llm

def sentiment_analyst(state: AgentState):
    print(f"🧠 [Analyst] Délibération en cours...")
    
    llm = get_llm(temperature=0.1) # Faible temp pour être rationnel
    
    prompt = f"""
    Tu es un Trader Expert en Gestion de Risque.
    
    DONNÉES DU MARCHÉ ({state['symbol']}):
    1. PRIX: {state['price']}$ (Position actuelle: {state['position_qty']} actions)
    2. SENTIMENT SOCIAL: {state['social_sentiment']} (sur une échelle de -1 à 1)
    3. TECHNIQUE (RSI): {state['rsi']}
    
    STRATÉGIE:
    - ACHETER (buy) si Sentiment > 0.2 ET RSI < 70 (Pas encore en surachat).
    - VENDRE (sell) si Sentiment < -0.2 OU RSI > 80 (Crash imminent ou surachat).
    - SINON: ATTENDRE (hold).
    
    Ta réponse doit être STRICTEMENT au format JSON:
    {{
      "decision": "buy/sell/hold",
      "reason": "Explication courte"
    }}
    """
    
    try:
        response = llm.invoke(prompt).content.strip()
        
        # Parsing un peu robuste (parfois le LLM met du markdown ```json ... ```)
        import json
        clean_json = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        print(f"💡 Décision IA: {data['decision'].upper()} ({data['reason']})")
        return {"decision": data['decision'], "reasoning": data['reason']}
        
    except Exception as e:
        print(f"❌ Erreur Analyste (JSON invalide ?): {e}")
        return {"decision": "hold", "reasoning": "Error parsing decision"}
    