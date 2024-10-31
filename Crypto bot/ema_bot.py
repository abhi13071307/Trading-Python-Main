import os
import time
import requests
import hmac
import hashlib
from collections import deque
from dotenv import load_dotenv

# Load API keys from environment variables
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
BASE_URL = "https://testnet.binance.vision"  # Binance Testnet base URL

# Parameters
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
EMA_50_PERIOD = 50
EMA_200_PERIOD = 200
DIFFERENCE_QUEUE = deque(maxlen=200)
TP_PERCENTAGE = 0.10
SL_PERCENTAGE = 0.08
QUANTITY = 0.001

# Function to fetch candle data
def fetch_candles():
    url = f"{BASE_URL}/api/v3/klines"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": 200
    }
    response = requests.get(url, params=params)
    data = response.json()
    closes = [float(c[4]) for c in data]  # Extract closing prices
    return closes

# Function to calculate EMA
def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]  # Start with SMA
    for price in prices[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema[-1]  # Return the latest EMA value

# Function to create HMAC signature
def create_signature(query_string):
    return hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# Function to place market order
def place_order(side):
    url = f"{BASE_URL}/api/v3/order"
    entry_price = float(fetch_candles()[-1])  # Using last close as entry price for example

    tp_price = entry_price * (1 + TP_PERCENTAGE if side == "BUY" else 1 - TP_PERCENTAGE)
    sl_price = entry_price * (1 - SL_PERCENTAGE if side == "BUY" else 1 + SL_PERCENTAGE)

    # Market order parameters
    params = {
        "symbol": SYMBOL,
        "side": side,
        "type": "MARKET",
        "quantity": QUANTITY,
        "recvWindow": 5000,
        "timestamp": int(time.time() * 1000)
    }
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    params["signature"] = create_signature(query_string)
    headers = {"X-MBX-APIKEY": API_KEY}

    # Place market order
    response = requests.post(url, headers=headers, params=params)
    print(f"Market order placed: {side} at {entry_price}")

    # Place TP and SL as limit orders
    tp_side = "SELL" if side == "BUY" else "BUY"
    sl_side = tp_side

    tp_params = {
        "symbol": SYMBOL,
        "side": tp_side,
        "type": "LIMIT",
        "quantity": QUANTITY,
        "price": round(tp_price, 2),
        "timeInForce": "GTC",
        "recvWindow": 5000,
        "timestamp": int(time.time() * 1000)
    }
    tp_params["signature"] = create_signature("&".join([f"{k}={v}" for k, v in tp_params.items()]))
    sl_params = {
        "symbol": SYMBOL,
        "side": sl_side,
        "type": "LIMIT",
        "quantity": QUANTITY,
        "price": round(sl_price, 2),
        "timeInForce": "GTC",
        "recvWindow": 5000,
        "timestamp": int(time.time() * 1000)
    }
    sl_params["signature"] = create_signature("&".join([f"{k}={v}" for k, v in sl_params.items()]))

    requests.post(url, headers=headers, params=tp_params)
    requests.post(url, headers=headers, params=sl_params)
    print(f"TP at {tp_price} and SL at {sl_price} placed.")

def main():
    print("Bot is running...")
    while True:
        closes = fetch_candles()
        ema_50 = calculate_ema(closes, EMA_50_PERIOD)
        ema_200 = calculate_ema(closes, EMA_200_PERIOD)
        difference = ema_50 - ema_200

        if DIFFERENCE_QUEUE:
            last_difference = DIFFERENCE_QUEUE[-1]
            if last_difference > 0 > difference:
                print("EMA crossover detected: SELL signal")
                place_order("SELL")
            elif last_difference < 0 < difference:
                print("EMA crossover detected: BUY signal")
                place_order("BUY")

        DIFFERENCE_QUEUE.append(difference)
        time.sleep(3600)  # Wait for the next hour

if __name__ == "__main__":
    main()
