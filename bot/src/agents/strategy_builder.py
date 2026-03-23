import json
import logging
from typing import Dict, Any
from ..shared.state import AgentState
from ..shared.llm_client import get_llm

logger = logging.getLogger("head_trader")

def build_strategy(state: AgentState) -> Dict[str, Any]:
    symbol = state.get('symbol', 'UNKNOWN')
    price = state.get('price', 0.0)
    
    print(f"⚖️ [Head Trader] Débat en cours pour {symbol}...")
    
    prompt = f"""
    Tu es le Head Trader d'un fonds d'investissement. Tranche le débat entre tes analystes pour {symbol} (Prix actuel: {price}).
    
    RAPPORTS DES ANALYSTES:
    - Marché (Macro): {state.get('market_regime', {})}
    - Technique: {state.get('technical_report', {})}
    - Fondamental: {state.get('fundamental_report', {})}
    - Sentiment: {state.get('sentiment_report', {})}
    - Portefeuille: {state.get('portfolio_report', {})}
    
    INSTRUCTIONS:
    Si le marché est Risk-On, privilégie la Technique et le Sentiment.
    Si le marché est Risk-Off, sois extrêmement strict sur le Fondamental.
    
    Retourne UNIQUEMENT un JSON valide avec cette structure exacte, sans markdown :
    {{
        "decision": "buy" | "sell" | "hold",
        "reasoning": "Explication de ton choix face aux contradictions",
        "strategy": {{
            "entry_price": {price},
            "sl_level": 0.0,
            "position_size": 0
        }}
    }}
    """
    
    try:
        llm = get_llm(temperature=0.1)
        response = llm.invoke(prompt).content.strip()
        
        # Nettoyage et parsing du JSON
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
            
        data = json.loads(response)
        
        logger.info(f"✅ Décision LLM: {data.get('decision').upper()} - {data.get('reasoning')}")
        return {
            "decision": data.get("decision", "hold"),
            "strategy": data.get("strategy", {}),
            "reasoning": data.get("reasoning", "")
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur Head Trader LLM: {e}")
        return {"decision": "hold", "reasoning": "Fallback suite erreur LLM"}
    