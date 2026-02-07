import requests
import os
import logging
import json
from ..shared.llm_client import get_llm

logger = logging.getLogger("discovery")

class DiscoveryAgent:
    def __init__(self):
        self.llm = get_llm(temperature=0)
        self.api_key = os.getenv("NEWS_API_KEY")
        self.fallback_symbols = ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "GOOGL", "META"]

    def scan_market(self):
        logger.info("🔭 [Discovery] Scan des news financières (NewsAPI)...")
        
        market_news = ""
        try:
            # On cherche les news sur le marché boursier des dernières 24h
            url = f"https://newsapi.org/v2/everything?q=stock+market+analysis+trending&sortBy=publishedAt&language=en&apiKey={self.api_key}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                articles = resp.json().get('articles', [])[:10] # Top 10 articles
                for art in articles:
                    market_news += f"- {art['title']}\n"
            else:
                raise Exception(f"NewsAPI Error: {resp.status_code}")

        except Exception as e:
            logger.warning(f"⚠️ Erreur NewsAPI ({e}), passage en mode secours.")
            return self.fallback_symbols

        # Extraction par l'IA (Qwen sur ton GPU !)
        prompt = f"""
        Identifie les 3 à 5 tickers boursiers (ex: NVDA, TSLA) les plus pertinents dans ces titres :
        {market_news}
        Réponds UNIQUEMENT avec une liste JSON de chaînes de caractères.
        """
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            # On cherche le JSON dans la réponse
            start, end = response.find('['), response.rfind(']') + 1
            if start != -1:
                return json.loads(response[start:end])
        except:
            pass
            
        return self.fallback_symbols
    