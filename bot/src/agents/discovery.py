import logging
import asyncio
import aiohttp
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Modèle de données
class DiscoveryCandidate(BaseModel):
    symbol: str
    name: str
    price_usd: float
    price_change_1h_pct: float
    price_change_24h_pct: float
    volume_24h_usd: float
    volume_change_pct: float
    market_cap_usd: float
    age_days: int
    discovery_score: float
    key_signals: List[str]

class DiscoveryAgent:
    def __init__(self, coingecko_api_key: str = None):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = coingecko_api_key
        self.session = None
        self.filters = {
            "min_volume_24h": 100_000,    # $100k min
            "volume_explosion": 2.0,      # x2 volume
            "price_move_threshold": 3.0,  # +/-3%
            "min_market_cap": 1_000_000,  # $1M min
        }

    # --- PONT SYNCHRONE POUR LE MAIN.PY ---
    def scan_market(self) -> List[str]:
        """
        Wrapper appelé par main.py.
        Gère la boucle asynchrone pour éviter de modifier main.py.
        """
        print("🔍 [Discovery] Démarrage du scan asynchrone...")
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self.run_discovery_cycle())
            
            # Extraction simple des symboles pour le bot
            symbols = [c['symbol'].upper() for c in result.get('top_opportunities', [])]
            
            if not symbols:
                logger.warning("⚠️ Aucune opportunité trouvée, fallback.")
                return ["BTC", "ETH", "DOGE"]
                
            return symbols
            
        except Exception as e:
            logger.error(f"❌ Erreur critique Discovery Sync: {e}")
            return ["BTC", "ETH"]

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "DiscoveryBot/1.0"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_top_coins(self, per_page: int = 250) -> List[Dict]:
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "1h,24h"
        }
        if self.api_key:
            params["x_cg_pro_api_key"] = self.api_key
            
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
        except Exception:
            return []

    def calculate_discovery_score(self, coin: Dict) -> DiscoveryCandidate:
        signals = []
        score = 0.0
        
        p24 = coin.get('price_change_percentage_24h') or 0.0
        p1h = coin.get('price_change_percentage_1h_in_currency') or 0.0
        vol = coin.get('total_volume') or 0.0
        mcap = coin.get('market_cap') or 0.0
        
        if abs(p24) > self.filters['price_move_threshold']:
            score += 0.3
            signals.append(f"Volatilité {p24:.1f}%")
        
        if abs(p1h) > 1.0:
            score += 0.4
            signals.append(f"Push 1h {p1h:.1f}%")
        
        if vol > self.filters['min_volume_24h']: score += 0.2
        if mcap > self.filters['min_market_cap']: score += 0.1

        return DiscoveryCandidate(
            symbol=str(coin['symbol']).upper(),
            name=coin.get('name', 'Unknown'),
            price_usd=float(coin.get('current_price') or 0),
            price_change_1h_pct=float(p1h),
            price_change_24h_pct=float(p24),
            volume_24h_usd=float(vol),
            volume_change_pct=0.0,
            market_cap_usd=float(mcap),
            age_days=0,
            discovery_score=round(score, 2),
            key_signals=signals
        )

    async def discover_candidates(self, max_results: int = 5) -> List[DiscoveryCandidate]:
        coins = await self.fetch_top_coins(250)
        candidates = []
        for coin in coins:
            try:
                cand = self.calculate_discovery_score(coin)
                if cand.discovery_score >= 0.4:
                    candidates.append(cand)
            except Exception:
                continue
        candidates.sort(key=lambda x: x.discovery_score, reverse=True)
        return candidates[:max_results]

    async def run_discovery_cycle(self) -> Dict[str, Any]:
        async with self:
            candidates = await self.discover_candidates(5)
            top_opps = [c.model_dump() for c in candidates]
            
            logger.info(f"✅ {len(top_opps)} opportunités identifiées.")
            for c in top_opps:
                print(f"   👉 {c['symbol']} (Score: {c['discovery_score']})")
            
            return {"top_opportunities": top_opps}
        