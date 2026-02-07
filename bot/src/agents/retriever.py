import requests
import yfinance as yf
import logging
from ..shared.state import AgentState

GATEWAY_URL = "http://gateway:8000"
logger = logging.getLogger("retriever")

def fetch_live_price(symbol: str) -> float:
    """Récupère le prix YFinance avec gestion des alias Crypto."""
    # Mapping des noms bruts vers format Yahoo (TICKER-USD)
    yahoo_map = {
        "SHIBA_INU": "SHIB-USD",
        "SHIB": "SHIB-USD",
        "DOGE": "DOGE-USD",
        "BITCOIN": "BTC-USD",
        "ETHEREUM": "ETH-USD"
    }
    
    # On nettoie le symbole
    clean_symbol = symbol.replace("-USD", "").upper()
    search_symbol = yahoo_map.get(clean_symbol, clean_symbol)
    
    try:
        # 1. Tentative directe
        ticker = yf.Ticker(search_symbol)
        price = ticker.fast_info.get('last_price')
        
        # 2. Si échec, tentative avec suffixe standard -USD (si pas déjà fait)
        if not price and "-USD" not in search_symbol:
             ticker = yf.Ticker(f"{search_symbol}-USD")
             price = ticker.fast_info.get('last_price')
             
        if price:
            logger.info(f"✅ Prix trouvé pour {search_symbol}: {price}$")
            return float(price)
            
    except Exception as e:
        logger.error(f"❌ Erreur YFinance pour {search_symbol}: {e}")
            
    return 0.0

def get_market_data(state: AgentState):
    symbol = state['symbol']
    print(f"📡 [Retriever] Récupération des données pour {symbol}...")
    
    qty = 0
    current_price = 0.0
    cash = 0.0
    
    # A. Gateway (Cash & Positions)
    try:
        acct_resp = requests.get(f"{GATEWAY_URL}/account", timeout=2)
        if acct_resp.status_code == 200:
            cash = float(acct_resp.json().get("cash", 0.0))

        pos_resp = requests.get(f"{GATEWAY_URL}/positions", timeout=2)
        if pos_resp.status_code == 200:
            for pos in pos_resp.json():
                if pos['symbol'] == symbol:
                    qty = int(pos['qty'])
                    current_price = float(pos['current_price'])
    except:
        pass

    # B. YFinance (si pas de prix via Alpaca)
    if current_price == 0:
        current_price = fetch_live_price(symbol)

    return {
        "position_qty": qty,
        "price": current_price,
        "cash": cash
    }
