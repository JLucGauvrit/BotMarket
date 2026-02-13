import requests
import yfinance as yf
import pandas as pd
import logging
from typing import Dict, Any
from ..shared.state import AgentState

GATEWAY_URL = "http://gateway:8000"
logger = logging.getLogger("retriever")

def clean_symbol(symbol: str) -> str:
    return symbol.upper().replace("/", "").replace("-USD", "")

def df_to_serializable(df: pd.DataFrame):
    if df.empty:
        return {}
    df = df.tail(90)
    return {
        "close": df["Close"].tolist(),
        "high": df["High"].tolist(),
        "low": df["Low"].tolist(),
        "volume": df["Volume"].tolist(),
    }

def retriever_node(state: AgentState) -> Dict[str, Any]:

    symbol = state.get("symbol")
    if not symbol:
        return {}

    logger.info(f"[Retriever] Fetching data for {symbol}")

    # ---- Yahoo ----
    price = 0.0
    history = {}

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="3mo")

        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            history = df_to_serializable(hist)

    except Exception as e:
        logger.warning(f"Yahoo error: {e}")

    # ---- Gateway ----
    qty = 0.0
    avg_entry = 0.0
    cash = 0.0

    try:
        acct = requests.get(f"{GATEWAY_URL}/account", timeout=2).json()
        cash = float(acct.get("cash", 0))

        positions = requests.get(f"{GATEWAY_URL}/positions", timeout=2).json()

        for pos in positions:
            if clean_symbol(pos["symbol"]) == clean_symbol(symbol):
                qty = float(pos["qty"])
                avg_entry = float(pos["avg_entry_price"])

    except Exception as e:
        logger.warning(f"Gateway error: {e}")

    return {
        "market": {
            "symbol": symbol,
            "price": price,
            "history": history,
        },
        "portfolio": {
            "position_qty": qty,
            "avg_entry_price": avg_entry,
            "cash": cash,
        }
    }

# Compatibilité
get_market_data = retriever_node
