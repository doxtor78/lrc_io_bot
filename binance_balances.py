import nest_asyncio
nest_asyncio.apply()

import requests
from binance.client import Client
import asyncio

def get_binance_balances(api_key, api_secret):
    # Ensure an event loop exists for python-binance in Flask threads
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    try:
        # Initialize Binance client
        client = Client(api_key, api_secret)
        # Get account information
        account = client.get_account()
        balances = []
        for asset in account['balances']:
            free = float(asset['free'])
            locked = float(asset['locked'])
            total = free + locked
            if total > 0:
                symbol = asset['asset']
                if symbol != 'USDT':
                    try:
                        ticker = client.get_symbol_ticker(symbol=f"{symbol}USDT")
                        price = float(ticker['price'])
                    except Exception:
                        continue
                else:
                    price = 1.0
                usd_value = total * price
                if usd_value == 0:
                    continue
                balances.append({
                    'asset': symbol,
                    'amount': total,
                    'price': price,
                    'usd_value': usd_value
                })
        return balances
    except Exception as e:
        print(f"Error retrieving Binance balances: {e}")
        return []

if __name__ == '__main__':
    api_key = '8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7'
    api_secret = 'jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO'
    balances = get_binance_balances(api_key, api_secret)
    # Filter for balances above $10
    filtered = [b for b in balances if b['usd_value'] > 10]
    if not filtered:
        print("No assets above $10 found.")
    else:
        total = sum(b['usd_value'] for b in filtered)
        print(f"{'Asset':<10} {'Amount':<15} {'Price (USD)':<15} {'Value (USD)':<15}")
        print("-" * 55)
        for b in filtered:
            print(f"{b['asset']:<10} {b['amount']:<15.8f} ${b['price']:<14.2f} ${b['usd_value']:<14.2f}")
        print("-" * 55)
        print(f"{'TOTAL':<10} {'':<15} {'':<15} ${total:<14.2f}") 