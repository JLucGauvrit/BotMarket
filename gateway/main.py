import os
from fastapi import FastAPI, HTTPException
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

app = FastAPI()

# Initialisation Alpaca
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
PAPER = os.getenv("ALPACA_PAPER", "True") == "True"

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=PAPER)

@app.get("/account")
def get_account():
    return trading_client.get_account()

@app.post("/order")
def place_order(symbol: str, side: str, qty: int = 1):
    # Traduction simple pour le Brain : "buy" -> OrderSide.BUY
    try:
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=side_enum,
            time_in_force=TimeInForce.GTC
        )
        return trading_client.submit_order(order_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    