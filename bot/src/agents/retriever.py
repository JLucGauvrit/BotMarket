import requests
import yfinance as yf
import logging
import pandas as pd
import asyncio
import aiohttp
from typing import Dict, Any, Tuple
from ..shared.state import AgentState

GATEWAY_URL = "http://gateway:8000"
logger = logging.getLogger("retriever")

# Cache pour éviter de spammer l'API de recherche CoinGecko
COIN_ID_CACHE = {
    "BTC": "bitcoin", 
    "ETH": "ethereum", 
    "DOGE": "dogecoin",
    "SOL": "solana", 
    "ADA": "cardano",
    "SHIB": "shiba-inu",
    "XRP": "ripple"
}

def _is_likely_crypto(symbol: str) -> bool:
    """Heuristique: symbols courts sans '.', ']' = probablement crypto."""
    clean = symbol.upper().strip()
    return len(clean) <= 6 and "." not in clean

async def get_coingecko_id(session, symbol: str) -> str:
    """Trouve dynamiquement l'ID CoinGecko (ex: 'ASTER' -> 'aster-protocol')."""
    symbol_upper = symbol.upper()
    
    # 1. Vérifier le cache
    if symbol_upper in COIN_ID_CACHE:
        return COIN_ID_CACHE[symbol_upper]
    
    # 2. Rechercher via API
    url = "https://api.coingecko.com/api/v3/search"
    params = {"query": symbol}
    try:
        async with session.get(url, params=params, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                coins = data.get("coins", [])
                # On prend le premier match exact sur le symbole
                for coin in coins:
                    if coin["symbol"].upper() == symbol_upper:
                        found_id = coin["id"]
                        COIN_ID_CACHE[symbol_upper] = found_id # Mise en cache
                        return found_id
    except Exception as e:
        logger.debug(f"Search CoinGecko fail pour {symbol}: {e}")
    
    return None

async def fetch_crypto_price_coingecko(symbol: str) -> Tuple[float, str]:
    """Récupère prix crypto via ID dynamique."""
    try:
        async with aiohttp.ClientSession() as session:
            # Étape 1: Trouver l'ID
            coin_id = await get_coingecko_id(session, symbol)
            
            if not coin_id:
                return 0.0, symbol
                
            # Étape 2: Récupérer le prix
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": coin_id, "vs_currencies": "usd"}
            
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if coin_id in data and "usd" in data[coin_id]:
                        price = data[coin_id]["usd"]
                        logger.info(f"✅ Prix crypto {symbol} (ID: {coin_id}): ${price}")
                        return float(price), symbol
                        
    except Exception as e:
        logger.debug(f"CoinGecko price fail: {e}")
        
    return 0.0, symbol

def smart_fetch_price_and_history(symbol: str) -> Tuple[float, pd.DataFrame, str]:
    """Smart Fetch: Priorité Crypto (ID Dynamique) -> Fallback Action."""
    clean = symbol.upper().replace("/", "").replace("-USD", "")
    if clean.endswith("USD") and len(clean) > 3:
        clean = clean[:-3]
    
    # 1. Tentative Crypto (CoinGecko Dynamique)
    if _is_likely_crypto(clean):
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            price, valid_sym = loop.run_until_complete(fetch_crypto_price_coingecko(clean))
            if price > 0:
                # Pas d'historique pour l'instant via CoinGecko Free
                return price, pd.DataFrame(), valid_sym
        except Exception:
            pass
    
    # 2. Fallback YFinance (Actions)
    # On rend Yahoo silencieux pour éviter les erreurs 404 dans les logs
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    
    candidates = [symbol, clean, f"{clean}-USD"]
    candidates = list(dict.fromkeys(candidates))

    for candidate in candidates:
        try:
            ticker = yf.Ticker(candidate)
            price = ticker.fast_info.get('last_price')
            
            if not price: continue
                
            df = ticker.history(period="3mo")
            if not df.empty:
                df.index = df.index.astype(str) # Fix Timestamp error
                logger.info(f"✅ Données Yahoo {candidate}: ${price:.2f}")
                # Rétablir logs
                logging.getLogger("yfinance").setLevel(logging.WARNING)
                return float(price), df, candidate
        except Exception:
            continue
    
    # Rétablir logs
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logger.warning(f"⚠️ Prix introuvable pour {symbol}")
    return 0.0, pd.DataFrame(), symbol

def get_market_data(state: AgentState) -> Dict[str, Any]:
    symbol = state.get('symbol', 'UNKNOWN')
    print(f"📡 [Retriever] Récupération pour {symbol}...")
    
    # 1. Gateway (Positions)
    qty, current_price, cash, avg_entry = 0, 0.0, 0.0, 0.0
    try:
        acct = requests.get(f"{GATEWAY_URL}/account", timeout=2).json()
        cash = float(acct.get("cash", 0))
        
        positions = requests.get(f"{GATEWAY_URL}/positions", timeout=2).json()
        for pos in positions:
            p_sym = pos['symbol'].replace("/", "").replace("-USD", "")
            s_sym = symbol.replace("/", "").replace("-USD", "")
            if p_sym in s_sym or s_sym in p_sym:
                qty = int(float(pos['qty']))
                current_price = float(pos['current_price'])
                avg_entry = float(pos['avg_entry_price'])
    except: pass
    
    # 2. Smart Fetch
    yf_price, df, valid_symbol = smart_fetch_price_and_history(symbol)
    if yf_price > 0: current_price = yf_price
    
    # Update State
    state["prices_df"] = df
    
    return {
        "position_qty": qty,
        "price": current_price,
        "cash": cash,
        "avg_entry_price": avg_entry,
        "symbol": valid_symbol
    }
