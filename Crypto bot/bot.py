import os
import time
import hmac
import hashlib
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

BASE_URL = "https://testnet.binancefuture.com/fapi/v1"

def create_signature(params):
    """Create a signature for the API request."""
    query_string = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
    return hmac.new(os.getenv('BINANCE_API_SECRET').encode(), query_string.encode(), hashlib.sha256).hexdigest()

def get_server_time():
    """Get the current server time from Binance."""
    url = f"{BASE_URL}/time"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['serverTime']
    else:
        print("Error getting server time:", response.status_code, response.text)
        return None

def place_order(symbol, side, quantity, order_type='MARKET'):
    """Place a market order on the Binance Testnet."""
    url = f"{BASE_URL}/order"
    api_key = os.getenv('BINANCE_API_KEY')

    timestamp = get_server_time()
    if timestamp is None:
        return None

    params = {
        'symbol': symbol,
        'side': side,
        'type': order_type,
        'quantity': quantity,
        'timestamp': timestamp,
        'recvWindow': 5000
    }

    params['signature'] = create_signature(params)

    headers = {
        'X-MBX-APIKEY': api_key
    }

    response = requests.post(url, headers=headers, params=params)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return None

    return response.json()

def cancel_order(symbol, order_id):
    """Cancel a specific order."""
    url = f"{BASE_URL}/order"
    api_key = os.getenv('BINANCE_API_KEY')

    timestamp = get_server_time()
    if timestamp is None:
        return None

    params = {
        'symbol': symbol,
        'orderId': order_id,
        'timestamp': timestamp,
        'recvWindow': 5000
    }

    params['signature'] = create_signature(params)

    headers = {
        'X-MBX-APIKEY': api_key
    }

    response = requests.delete(url, headers=headers, params=params)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return None

    return response.json()

def get_open_orders(symbol):
    """Get all open orders for a specific symbol."""
    url = f"{BASE_URL}/openOrders"
    api_key = os.getenv('BINANCE_API_KEY')

    timestamp = get_server_time()
    if timestamp is None:
        return None

    params = {
        'symbol': symbol,
        'timestamp': timestamp,
        'recvWindow': 5000
    }

    params['signature'] = create_signature(params)

    headers = {
        'X-MBX-APIKEY': api_key
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return None

    return response.json()

def get_wallet_balance():
    """Get wallet balance from Binance Testnet."""
    url = f"{BASE_URL}/balance"
    api_key = os.getenv('BINANCE_API_KEY')

    timestamp = get_server_time()
    if timestamp is None:
        return None

    params = {
        'timestamp': timestamp,
        'recvWindow': 5000
    }

    params['signature'] = create_signature(params)

    headers = {
        'X-MBX-APIKEY': api_key
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return None

    return response.json()

def main():
    while True:
        print("\n=== Binance Testnet Bot Menu ===")
        print("1. Place Order")
        print("2. Cancel Order")
        print("3. View Open Orders")
        print("4. View Wallet Balance")
        print("5. Exit")

        choice = input("Select an option (1-5): ")

        if choice == '1':
            symbol = input("Enter symbol (e.g., BTCUSDT): ")
            side = input("Enter side (BUY or SELL): ")
            quantity = float(input("Enter quantity: "))
            response = place_order(symbol, side, quantity)
            print("Order response:", response)

        elif choice == '2':
            symbol = input("Enter symbol (e.g., BTCUSDT): ")
            order_id = int(input("Enter order ID to cancel: "))
            print("Waiting for 10 seconds before canceling the order...")
            time.sleep(10)
            response = cancel_order(symbol, order_id)
            print("Cancel order response:", response)

        elif choice == '3':
            symbol = input("Enter symbol (e.g., BTCUSDT): ")
            response = get_open_orders(symbol)
            print("Open orders response:", response)

        elif choice == '4':
            response = get_wallet_balance()
            print("Wallet balance response:", response)

        elif choice == '5':
            print("Exiting the program.")
            break

        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
