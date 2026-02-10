"""
DISCOVERY AGENT V3 - DEFENSIVE & ROBUST 🛡️
- Fix: Gestion des erreurs 'NoneType' (result.get, session.get)
- Mode: Hybride (Crypto Trending + Stocks Volatiles)
"""

import logging
import asyncio
import random
import aiohttp
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Modèle de données
class DiscoveryCandidate(BaseModel):
    symbol: str
    name: str
    price_usd: float
    price_change_1h_pct: float
    price_change_24h_pct: float
    volume_24h_usd: float
    market_cap_usd: float
    discovery_score: float
    key_signals: List[str]
    asset_type: str = "crypto"

class DiscoveryAgent:
    def __init__(self, coingecko_api_key: Optional[str] = None):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = None
        
        # Liste de secours "Spicy" (Volatiles & Tech & Crypto-Stocks)
        self.spicy_stocks = [
            "COIN", "MSTR", "MARA", "PLTR", "AMD", "SMCI", 
            "NET", "DKNG", "RBLX", "U", "AI", "SOFI"
        ]

    # --- GESTIONNAIRE DE CONTEXTE ASYNCHRONE ---
    async def __aenter__(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    # --- PONT SYNCHRONE POUR MAIN.PY ---
    def scan_market(self) -> List[str]:
        """Wrapper appelé par main.py."""
        print("🔭 [Discovery] Scan des pépites (Trending & Gainers)...")
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self.run_discovery_cycle())
            
            # --- FIX CRITIQUE: Protection contre result=None ---
            if result is None:
                logger.warning("⚠️ Discovery a renvoyé None, utilisation fallback.")
                result = {} 
            
            # 1. Top 5 Cryptos
            raw_cryptos = [c['symbol'].upper() for c in result.get('top_opportunities', [])]
            top_cryptos = raw_cryptos[:5] 
            
            # 2. Injection Stocks (Top 3)
            random.shuffle(self.spicy_stocks)
            top_stocks = self.spicy_stocks[:3]
            
            logger.info(f"🍹 Mix Hybride: {top_cryptos} + {top_stocks}")
            
            # 3. Fusion et Déduplication
            final_list = list(set(top_cryptos + top_stocks))
            return final_list
            
        except Exception as e:
            logger.error(f"❌ Crash Discovery Sync: {e}")
            return random.sample(self.spicy_stocks, 4)

    # --- STRATEGIE 1 : LA HYPE (Trending Search) ---
    async def fetch_trending_coins(self) -> List[DiscoveryCandidate]:
        url = f"{self.base_url}/search/trending"
        candidates = []
        try:
            # Sécurité si session est None
            if not self.session: self.session = aiohttp.ClientSession()

            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Sécurité si data est None
                    if not data: return []

                    for item in data.get("coins", []):
                        c = item["item"]
                        rank = c.get("market_cap_rank")
                        if rank and rank > 3000: continue 
                        
                        cand = DiscoveryCandidate(
                            symbol=c["symbol"].upper(),
                            name=c["name"],
                            price_usd=0.0,
                            price_change_1h_pct=0.0,
                            price_change_24h_pct=0.0,
                            volume_24h_usd=0.0,
                            market_cap_usd=0.0,
                            discovery_score=0.9,
                            key_signals=["🔥 TRENDING"],
                            asset_type="crypto"
                        )
                        candidates.append(cand)
        except Exception:
            pass
        return candidates

    # --- STRATEGIE 2 : LE MOMENTUM (Volatilité) ---
    async def fetch_market_movers(self) -> List[DiscoveryCandidate]:
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "volume_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "1h,24h"
        }
        candidates = []
        try:
            # Sécurité si session est None
            if not self.session: self.session = aiohttp.ClientSession()

            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if not data: return [] # Sécurité

                    for coin in data:
                        # Sécurité si coin est None
                        if not coin: continue

                        score = 0.0
                        signals = []
                        p24 = coin.get("price_change_percentage_24h") or 0
                        vol = coin.get("total_volume") or 0
                        mcap = coin.get("market_cap") or 0
                        
                        if mcap < 1_000_000: continue
                        
                        if p24 > 10.0: score += 0.4; signals.append(f"Pump 24h {p24:.0f}%")
                        if mcap > 0 and (vol / mcap) > 0.2: score += 0.2; signals.append("High Vol")

                        if score >= 0.5:
                            cand = DiscoveryCandidate(
                                symbol=coin["symbol"].upper(),
                                name=coin["name"],
                                price_usd=coin["current_price"],
                                price_change_1h_pct=0.0,
                                price_change_24h_pct=p24,
                                volume_24h_usd=vol,
                                market_cap_usd=mcap,
                                discovery_score=score,
                                key_signals=signals
                            )
                            candidates.append(cand)
        except Exception:
            pass
        return candidates

    async def run_discovery_cycle(self) -> Dict[str, Any]:
        """Combine Trending + Movers."""
        try:
            async with self:
                t_trending = asyncio.create_task(self.fetch_trending_coins())
                t_movers = asyncio.create_task(self.fetch_market_movers())
                
                res_trend = await t_trending
                res_move = await t_movers
                
                all_cand = res_trend + res_move
                
                # Dedupe par symbole
                unique = {c.symbol: c for c in all_cand}.values()
                sorted_cand = sorted(list(unique), key=lambda x: x.discovery_score, reverse=True)
                
                top_opps = [c.model_dump() for c in sorted_cand[:7]]
                return {"top_opportunities": top_opps}
        except Exception as e:
            logger.error(f"❌ Erreur cycle async: {e}")
            return {"top_opportunities": []}
        