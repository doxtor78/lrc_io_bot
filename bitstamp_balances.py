import requests
import hmac
import hashlib
import time
import base64
import json

# Bitstamp API credentials
BITSTAMP_API_KEY = 'jihKE0CWGln3A1mczdKTUoazcfqPnQSb'
BITSTAMP_API_SECRET = 'FNxEXCRiJaEOC6BXmJ7KIvK7imZ6GRKP'
BITSTAMP_CUSTOMER_ID = 'jklv7730'

def bitstamp_request(endpoint, params=None):
    """Make a request to the Bitstamp API."""
    url = f'https://www.bitstamp.net/api/v2/{endpoint}/'
    nonce = str(int(time.time() * 1000))
    message = nonce + BITSTAMP_CUSTOMER_ID + BITSTAMP_API_KEY
    signature = hmac.new(
        BITSTAMP_API_SECRET.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest().upper()
    data = {
        'key': BITSTAMP_API_KEY,
        'signature': signature,
        'nonce': nonce,
    }
    if params:
        data.update(params)
    response = requests.post(url, data=data)
    return response.json()

def get_bitstamp_balances():
    response = bitstamp_request('balance')
    print("Bitstamp API Response:", response)  # Print raw API response for debugging
    if 'error' in response:
        print("Bitstamp API error:", response['error'])
        return []
    balances = []
    for asset_field, amount in response.items():
        if not asset_field.endswith('_balance'):
            continue
        asset = asset_field.replace('_balance', '')
        try:
            amount_f = float(amount)
        except Exception:
            continue
        if amount_f > 0:
            balances.append({'asset': asset, 'amount': amount_f})
    # Get current prices for crypto assets from Bitstamp public API
    if balances:
        for balance in balances:
            asset = balance['asset']
            # Skip fiat currencies (usd, eur, gbp, etc.)
            if asset in ['usd', 'eur', 'gbp']:
                balance['price'] = 1.0
                balance['value'] = balance['amount']
                continue
            ticker_url = f'https://www.bitstamp.net/api/v2/ticker/{asset}usd/'
            ticker_response = requests.get(ticker_url)
            try:
                ticker_data = ticker_response.json()
                if 'last' in ticker_data:
                    price = float(ticker_data['last'])
                    balance['price'] = price
                    balance['value'] = balance['amount'] * price
                else:
                    balance['price'] = 0.0
                    balance['value'] = 0.0
                    print(f"No price found for {asset}")
            except Exception:
                balance['price'] = 0.0
                balance['value'] = 0.0
                print(f"No price found for {asset}")
    return balances

if __name__ == '__main__':
    balances = get_bitstamp_balances()
    if balances:
        print("Bitstamp Balances:")
        print("Asset      Amount          Price (USD)     Value (USD)")
        print("-------------------------------------------------------")
        for balance in balances:
            print(f"{balance['asset']:<10} {balance['amount']:<15.8f} ${balance.get('price', 0):<15.2f} ${balance.get('value', 0):<15.2f}")
        total = sum(balance.get('value', 0) for balance in balances)
        print("-------------------------------------------------------")
        print(f"TOTAL                                      ${total:<15.2f}")
    else:
        print("No balances found or an error occurred.") 