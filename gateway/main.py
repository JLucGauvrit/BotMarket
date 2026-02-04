import os
import logging
from fastapi import FastAPI, HTTPException
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Configuration des logs pour voir ce qui se passe dans Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

app = FastAPI()

# 1. Récupération des clés (nettoyage des espaces éventuels)
API_KEY = os.getenv("ALPACA_API_KEY", "").strip()
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "").strip()

# 2. Gestion stricte du mode Paper
# On s'assure que si la clé commence par "PK", on force le mode Paper
PAPER_ENV = os.getenv("ALPACA_PAPER", "True").strip().lower()
IS_PAPER = PAPER_ENV == "true" or API_KEY.startswith("PK")

# 3. Initialisation du client avec l'URL de base explicite
# Le SDK utilise https://paper-api.alpaca.markets si paper=True
try:
    trading_client = TradingClient(
        api_key=API_KEY, 
        secret_key=SECRET_KEY, 
        paper=IS_PAPER
    )
    logger.info(f"🚀 Gateway connectée : Mode Paper={IS_PAPER}")
except Exception as e:
    logger.error(f"❌ Erreur d'initialisation Alpaca : {e}")

@app.get("/account")
def get_account():
    try:
        # Renvoie les informations du compte (Equity, Buying Power, etc.)
        return trading_client.get_account()
    except Exception as e:
        logger.error(f"Erreur Account: {e}")
        raise HTTPException(status_code=401, detail=f"Alpaca Auth Error: {e}")

@app.get("/positions")
def get_positions():
    try:
        # Récupère toutes les positions ouvertes
        return trading_client.get_all_positions()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/order")
def place_order(symbol: str, side: str, qty: int = 1):
    try:
        # Traduction du côté de l'ordre
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        
        # Création de la requête d'ordre au marché
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side_enum,
            time_in_force=TimeInForce.GTC
        )
        return trading_client.submit_order(order_data)
    except Exception as e:
        logger.error(f"Erreur Order: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    