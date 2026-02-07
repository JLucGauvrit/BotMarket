from ..shared.state import AgentState
from ..shared.llm_client import get_llm

# bot/src/agents/analyst.py
def sentiment_analyst(state: AgentState):
    # FORCE BUY POUR TESTER L'EXECUTOR
    print("🧪 [DEBUG] Forçage de la décision à BUY")
    return {"decision": "buy", "reasoning": "Test technique force buy"}