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

async def fetch_crypto_data_coingecko(symbol: str) -> Tuple[float, pd.DataFrame, str]:
    """Récupère le prix ET l'historique via CoinGecko (Fallback complet)."""
    try:
        async with aiohttp.ClientSession() as session:
            coin_id = await get_coingecko_id(session, symbol)
            if not coin_id: return 0.0, pd.DataFrame(), symbol
            
            # 1. Prix Actuel
            price = 0.0
            url_price = "https://api.coingecko.com/api/v3/simple/price"
            async with session.get(url_price, params={"ids": coin_id, "vs_currencies": "usd"}, timeout=3) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = float(data.get(coin_id, {}).get("usd", 0.0))
                    logger.info(f"✅ Prix CoinGecko {symbol}: ${price}")

            # 2. Historique des prix (90 jours) pour le Technicien
            df = pd.DataFrame()
            if price > 0:
                url_hist = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                async with session.get(url_hist, params={"vs_currency": "usd", "days": "90"}, timeout=3) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "prices" in data:
                            df = pd.DataFrame(data["prices"], columns=["Date", "Close"])
                            df["Date"] = pd.to_datetime(df["Date"], unit="ms")
                            df.set_index("Date", inplace=True)
                            df.index = df.index.strftime('%Y-%m-%d')
                            logger.info(f"✅ Historique CoinGecko récupéré pour {symbol} ({len(df)} jours)")

            return price, df, symbol
    except Exception as e:
        logger.error(f"❌ Erreur CoinGecko: {e}")
    
    return 0.0, pd.DataFrame(), symbol

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
        
        # Appel de la NOUVELLE fonction
        cg_price, cg_df, valid_symbol = loop.run_until_complete(fetch_crypto_data_coingecko(clean))
        
        if cg_price > 0:
            return cg_price, cg_df, valid_symbol
            
    except Exception as e:
        logger.error(f"Erreur Fallback CG: {e}")

    logger.warning(f"⚠️ Prix introuvable pour {symbol}")
    return 0.0, pd.DataFrame(), clean

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
        
        # Appel de la NOUVELLE fonction
        cg_price, cg_df, valid_symbol = loop.run_until_complete(fetch_crypto_data_coingecko(clean))
        
        if cg_price > 0:
            return cg_price, cg_df, valid_symbol
            
    except Exception as e:
        logger.error(f"Erreur Fallback CG: {e}")

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
