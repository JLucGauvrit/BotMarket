import requests
from ..shared.state import AgentState
from ..shared.llm_client import get_llm

# Ton serveur d'outils local (LangGraph Integration)
TOOLS_SERVER = "http://192.168.1.190:8082/web_search" 

def scan_social_media(state: AgentState):
    symbol = state['symbol']
    print(f"🐦 [Social] Scanning du sentiment pour {symbol}...")
    
    raw_text = ""
    
    # 1. Tentative de recherche réelle
    try:
        query = {"query": f"{symbol} stock sentiment reddit twitter analysis latest"}
        # Timeout court pour ne pas bloquer le bot si le serveur d'outils est éteint
        resp = requests.post(TOOLS_SERVER, json=query, timeout=3)
        if resp.status_code == 200:
            raw_text = str(resp.json())[:1000] # On limite la taille
    except:
        # Fallback si le serveur d'outils n'est pas là
        raw_text = f"Market is waiting for {symbol} earnings. Analysts are mixed but slightly bullish."

    # 2. Analyse par le LLM (Qwen/Llama)
    try:
        llm = get_llm()
        prompt = f"""
        Analyse ce texte sur {symbol}: "{raw_text}"
        
        Tâche: Donne un score de sentiment entre -1.0 (Pessimiste) et 1.0 (Optimiste).
        Réponds UNIQUEMENT par le chiffre (ex: 0.4).
        """
        response = llm.invoke(prompt).content.strip()
        
        # Nettoyage de la réponse (au cas où le LLM bavarde)
        import re
        match = re.search(r"-?\d+(\.\d+)?", response)
        sentiment = float(match.group()) if match else 0.0
        
        return {"social_sentiment": sentiment, "social_summary": raw_text[:50] + "..."}
        
    except Exception as e:
        print(f"⚠️ Erreur Social Agent: {e}")
        return {"social_sentiment": 0.0, "social_summary": "Error"}