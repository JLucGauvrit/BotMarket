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

# Cache pour CoinGecko
COIN_ID_CACHE = {
    "BTC": "bitcoin", "ETH": "ethereum", "DOGE": "dogecoin",
    "SOL": "solana", "SHIB": "shiba-inu"
}

async def get_coingecko_id(session, symbol: str) -> str:
    """Trouve l'ID CoinGecko dynamiquement."""
    symbol_upper = symbol.upper()
    if symbol_upper in COIN_ID_CACHE: return COIN_ID_CACHE[symbol_upper]
    
    url = "https://api.coingecko.com/api/v3/search"
    try:
        async with session.get(url, params={"query": symbol}, timeout=2) as resp:
            if resp.status == 200:
                data = await resp.json()
                for coin in data.get("coins", []):
                    if coin["symbol"].upper() == symbol_upper:
                        found_id = coin["id"]
                        COIN_ID_CACHE[symbol_upper] = found_id
                        return found_id
    except: pass
    return None

async def fetch_crypto_price_coingecko(symbol: str) -> Tuple[float, str]:
    """Récupère prix crypto via CoinGecko (Fallback)."""
    try:
        async with aiohttp.ClientSession() as session:
            coin_id = await get_coingecko_id(session, symbol)
            if not coin_id: return 0.0, symbol
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": coin_id, "vs_currencies": "usd"}
            async with session.get(url, params=params, timeout=3) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if coin_id in data:
                        price = data[coin_id]["usd"]
                        logger.info(f"✅ Prix CoinGecko {symbol}: ${price}")
                        return float(price), symbol
    except: pass
    return 0.0, symbol

def smart_fetch_price_and_history(symbol: str) -> Tuple[float, pd.DataFrame, str]:
    """
    Stratégie de récupération priorisée :
    1. Yahoo Finance (Actions: TSLA, AAPL)
    2. Yahoo Finance (Cryptos: BTC-USD)
    3. CoinGecko (Exotique: PIPPIN)
    """
    clean = symbol.upper().replace("/", "").replace("-USD", "")
    if clean.endswith("USD") and len(clean) > 3: clean = clean[:-3]

    # ORDRE IMPORTANT : On teste les tickers Yahoo d'abord
    candidates = [symbol, clean, f"{clean}-USD"]
    candidates = list(dict.fromkeys(candidates))

    # Silence Yahoo
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    for candidate in candidates:
        try:
            ticker = yf.Ticker(candidate)
            
            # Vérification via History (plus fiable que fast_info)
            hist = ticker.history(period="5d")
            
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                
                # Récup historique long pour le technicien
                df = ticker.history(period="3mo")
                if not df.empty:
                    df.index = df.index.strftime('%Y-%m-%d') # Fix Timestamp
                
                logging.getLogger("yfinance").setLevel(logging.WARNING)
                logger.info(f"✅ Données Yahoo {candidate}: ${price:.2f}")
                return price, df, candidate
                
        except: continue
    
    logging.getLogger("yfinance").setLevel(logging.WARNING)

    # Fallback CoinGecko (si Yahoo échoue)
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        cg_price, _ = loop.run_until_complete(fetch_crypto_price_coingecko(clean))
        if cg_price > 0:
            return cg_price, pd.DataFrame(), clean
    except: pass

    logger.warning(f"⚠️ Prix introuvable pour {symbol}")
    return 0.0, pd.DataFrame(), clean

def get_market_data(state: AgentState) -> Dict[str, Any]:
    symbol = state.get('symbol', 'UNKNOWN')
    print(f"📡 [Retriever] Récupération pour {symbol}...")
    
    # 1. Gateway
    qty, current_price, cash, avg_entry = 0, 0.0, 0.0, 0.0
    try:
        acct = requests.get(f"{GATEWAY_URL}/account", timeout=2).json()
        cash = float(acct.get("cash", 0))
        positions = requests.get(f"{GATEWAY_URL}/positions", timeout=2).json()
        for pos in positions:
            p_clean = pos['symbol'].replace("/", "").replace("-USD", "")
            s_clean = symbol.replace("/", "").replace("-USD", "")
            if p_clean == s_clean:
                qty = int(float(pos['qty']))
                current_price = float(pos['current_price'])
                avg_entry = float(pos['avg_entry_price'])
    except: pass
    
    # 2. Smart Fetch
    yf_price, df, valid_symbol = smart_fetch_price_and_history(symbol)
    if yf_price > 0: current_price = yf_price
    
    return {
        "position_qty": qty,
        "price": current_price,
        "cash": cash,
        "avg_entry_price": avg_entry,
        "symbol": valid_symbol,
        "prices_df": df  # <-- CRITIQUE : On retourne le DF explicitement
    }
