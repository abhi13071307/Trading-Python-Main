import threading
import time
import pandas as pd
import numpy as np
from binance.client import Client
import socketio
import hashlib
import hmac
import requests
import json
import os
from dotenv import load_dotenv

# Global Variables
bollinger_up = None
bollinger_down = None
current_rsi = None
current_market_price = None

# Binance API Credentials (replace with your credentials)
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("SECRET_KEY")
base_url = "https://fapi.pi42.com"

client = Client(API_KEY, API_SECRET)

# Pi42 WebSocket URL
server_url = 'https://fawss.pi42.com/'
sio = socketio.Client()


def generate_signature(api_secret, data_to_sign):
    return hmac.new(api_secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

# Function to fetch kline data from Binance
def fetch_kline_data(symbol, interval, limit=100):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                           'close_time', 'quote_asset_volume', 'number_of_trades', 
                                           'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 
                                           'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"Error fetching kline data: {e}")
        return pd.DataFrame()

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(data, period=20, std_dev=2):
    try:
        data['SMA'] = data['close'].rolling(window=period).mean()
        data['STD'] = data['close'].rolling(window=period).std()
        data['Upper'] = data['SMA'] + (std_dev * data['STD'])
        data['Lower'] = data['SMA'] - (std_dev * data['STD'])
        return data
    except Exception as e:
        print(f"Error calculating Bollinger Bands: {e}")
        return data

# Function to calculate RSI
def calculate_rsi(data, period=14):
    try:
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        return data
    except Exception as e:
        print(f"Error calculating RSI: {e}")
        return data

# Thread to update Bollinger Bands and RSI
def update_indicators():
    global bollinger_up, bollinger_down, current_rsi
    symbol = "BTCUSDT"
    interval = Client.KLINE_INTERVAL_5MINUTE

    while True:
        try:
            df = fetch_kline_data(symbol, interval)
            if df.empty:
                continue
            df = calculate_bollinger_bands(df)
            df = calculate_rsi(df)
            latest_data = df.iloc[-1]

            bollinger_up = latest_data['Upper']
            bollinger_down = latest_data['Lower']
            current_rsi = latest_data['RSI']

            print(f"\nUpdated Indicators: Bollinger Up = {bollinger_up:.2f}, Bollinger Down = {bollinger_down:.2f}, RSI = {current_rsi:.2f}")
        except Exception as e:
            print(f"Error updating indicators: {e}")

        time.sleep(60)  # Sleep for 5 minutes before fetching new data

# WebSocket Event Handlers
@sio.event
def connect():
    print("\nConnected to Pi42 WebSocket server.")
    sio.emit('subscribe', {'params': ['btcusdt@markPrice']})

@sio.event
def disconnect():
    print("Disconnected from Pi42 WebSocket server.")

@sio.on('markPriceUpdate')
def on_mark_price_update(data):
    global current_market_price
    try:
        # Extract the price from the WebSocket message and convert to float
        current_market_price = float(data['p'])  # Ensure it's a float
        
        print(f"\nUpdated Current Market Price: {current_market_price:.2f}")
        
        # Check the conditions for placing orders
        check_conditions_and_place_order()

    except KeyError:
        print("Error: Missing 'p' field in data")
    except ValueError:
        print("Error: Invalid market price data")

# Function to check conditions and place orders based on Bollinger Bands and RSI
def check_conditions_and_place_order():
    global current_market_price, bollinger_up, bollinger_down, current_rsi

    if current_market_price is None or bollinger_up is None or bollinger_down is None or current_rsi is None:
        return

    print("\nChecking conditions to place an order...")

    if current_market_price >= bollinger_up and current_rsi >= 70:
        print(f"Condition met for SELL: Market Price >= Bollinger Up ({current_market_price} >= {bollinger_up}) and RSI >= 70 ({current_rsi} >= 70).")
        place_order("SELL")
    elif current_market_price <= bollinger_down and current_rsi <= 30:
        print(f"Condition met for BUY: Market Price <= Bollinger Down ({current_market_price} <= {bollinger_down}) and RSI <= 30 ({current_rsi} <= 30).")
        place_order("BUY")
    else:
        print("No conditions met for order placement.")

# Function to place an order (empty for now)
def place_order(side):
    global current_market_price, bollinger_up, bollinger_down, current_rsi

    if current_market_price is None or bollinger_up is None or bollinger_down is None or current_rsi is None:
        print("Error: Missing required data for order placement.")
        return

    print(f"\nPlacing order with side: {side}")
    try:
        # Set the quantity you want to trade (for now, setting a placeholder)
        quantity = 0.02  # Placeholder for the quantity of the asset to trade (adjust as needed)

        # Calculate take profit and stop loss prices based on the current market price
        take_profit_price, stop_loss_price = calculate_take_profit_stop_loss(side, current_market_price)

        # Generate the current timestamp in milliseconds
        timestamp = str(int(time.time() * 1000))

        # Define the order parameters
        params = {
            'timestamp': timestamp,         # Current timestamp in milliseconds
            'placeType': 'ORDER_FORM',      # Type of order placement
            'quantity': quantity,           # Quantity of the asset to trade
            'side': side,                   # Order side, either 'BUY' or 'SELL'
            'symbol': 'BTCUSDT',            # Trading pair (e.g., BTC/USDT)
            'type': 'MARKET',               # Order type, 'MARKET' for market orders
            'reduceOnly': False,            # Whether to reduce an existing position only
            'marginAsset': 'USDT',          # The asset used as margin (USDT in this case)
            'deviceType': 'WEB',            # Device type (e.g., WEB, MOBILE)
            'userCategory': 'EXTERNAL',     # User category (e.g., EXTERNAL, INTERNAL)
            'takeProfitPrice': take_profit_price,  # Take profit price
            'stopLossPrice': stop_loss_price,      # Stop loss price
        }

        # Convert the parameters to a JSON string to sign
        data_to_sign = json.dumps(params, separators=(',', ':'))

        # Generate the signature for authentication
        signature = generate_signature(API_SECRET, data_to_sign)

        # Define the headers including the API key and the signature
        headers = {
            'api-key': API_KEY,
            'signature': signature,
        }

        # Send the POST request to place the order (simulate order placement)
        response = requests.post(f'{base_url}/v1/order/place-order', json=params, headers=headers)

        # Raise an HTTPError if the response status is 4xx or 5xx
        response.raise_for_status()

        # Parse the JSON response data
        response_data = response.json()

        # Print the success message with the order details
        print(f"Order placed successfully: {json.dumps(response_data, indent=4)}")

    except requests.exceptions.HTTPError as err:
        # Handle HTTP errors specifically
        print(f"Error: {err.response.text if err.response else err}")

    except Exception as e:
        # Handle any other unexpected errors
        print(f"An unexpected error occurred: {str(e)}")

# Function to calculate take profit and stop loss prices based on current market price
def calculate_take_profit_stop_loss(side, current_market_price):
    if side == 'BUY':
        take_profit_price = current_market_price * 1.002  # 0.2% up for BUY
        stop_loss_price = current_market_price * 0.995  # 0.5% down for BUY
    elif side == 'SELL':
        take_profit_price = current_market_price * 0.998  # 0.2% down for SELL
        stop_loss_price = current_market_price * 1.005  # 0.5% up for SELL
    else:
        raise ValueError("Invalid side value. Should be 'BUY' or 'SELL'.")
    
    return take_profit_price, stop_loss_price

# Thread to connect to WebSocket
def connect_to_websocket():
    while True:
        try:
            sio.connect(server_url)
            sio.wait()
        except Exception as e:
            print(f"Error in WebSocket connection: {e}")
            time.sleep(5)  # Retry after 5 seconds

# Main Function
if __name__ == "__main__":
    # Start the indicator update thread
    indicator_thread = threading.Thread(target=update_indicators, daemon=True)
    indicator_thread.start()

    # Start the WebSocket connection thread
    websocket_thread = threading.Thread(target=connect_to_websocket, daemon=True)
    websocket_thread.start()

    # Keep the main program running
    try:
        while True:
            time.sleep(1)  # Main thread keeps running
    except KeyboardInterrupt:
        print("Program interrupted, exiting...")
        sio.disconnect()  # Cleanly disconnect from WebSocket
