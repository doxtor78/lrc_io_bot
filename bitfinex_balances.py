import requests
import hmac
import hashlib
import time
import json
import base64

BITFINEX_API_KEY = 'cbb2e86f32e6b4256478f1d38bd8e88d725e6312940'
BITFINEX_API_SECRET = '171522474c91db9e7b144528d6cd82ffc10a4603114'

def bitfinex_public_request(endpoint):
    """Make a request to Bitfinex public API endpoints."""
    url = f'https://api.bitfinex.com/v1/{endpoint}'
    response = requests.get(url)
    print(f"Public API Response for {endpoint}:", response.text)
    return response.json()

def bitfinex_private_request(endpoint, params=None):
    """Make a request to Bitfinex private API endpoints."""
    url = f'https://api.bitfinex.com/v1/{endpoint}'
    nonce = str(int(time.time() * 1000))
    payload = {
        'request': f'/v1/{endpoint}',
        'nonce': nonce,
    }
    if params:
        payload.update(params)
    payload_json = json.dumps(payload)
    payload_base64 = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')
    print("Private API Payload:", payload_json)
    signature = hmac.new(
        BITFINEX_API_SECRET.encode('utf-8'),
        msg=payload_base64.encode('utf-8'),
        digestmod=hashlib.sha384
    ).hexdigest()
    headers = {
        'X-BFX-APIKEY': BITFINEX_API_KEY,
        'X-BFX-SIGNATURE': signature,
        'X-BFX-PAYLOAD': payload_base64,
    }
    response = requests.post(url, headers=headers)
    print(f"Private API Response for {endpoint}:", response.text)
    return response.json()

def test_bitfinex_connection():
    """Test connection to Bitfinex API using public endpoint."""
    try:
        response = bitfinex_public_request('pubticker/btcusd')
        print("Bitfinex API Connection Test:", response)
        return True
    except Exception as e:
        print("Error testing Bitfinex connection:", str(e))
        return False

def get_bitfinex_balances():
    """Fetch Bitfinex account balances."""
    try:
        response = bitfinex_private_request('balances')
        if isinstance(response, list):
            balances = []
            for balance in response:
                if balance.get('type') == 'exchange' and float(balance.get('amount', 0)) > 0:
                    balances.append({
                        'asset': balance['currency'],
                        'amount': float(balance['amount']),
                    })
            # Get current prices for all assets from Bitfinex public API
            if balances:
                for balance in balances:
                    asset = balance['asset']
                    if asset == 'usd':
                        balance['price'] = 1.0
                        balance['value'] = balance['amount']
                        continue
                    try:
                        ticker_data = bitfinex_public_request(f'pubticker/{asset}usd')
                        if 'last_price' in ticker_data:
                            price = float(ticker_data['last_price'])
                            balance['price'] = price
                            balance['value'] = balance['amount'] * price
                        else:
                            balance['price'] = 0.0
                            balance['value'] = 0.0
                            print(f"No price found for {asset}")
                    except Exception as e:
                        print(f"Error fetching price for {asset}:", str(e))
                        balance['price'] = 0.0
                        balance['value'] = 0.0
            return balances
        else:
            print("Unexpected response format:", response)
            return []
    except Exception as e:
        print("Error fetching Bitfinex balances:", str(e))
        return []

if __name__ == '__main__':
    if test_bitfinex_connection():
        balances = get_bitfinex_balances()
        if balances:
            print("\nBitfinex Balances:")
            print("Asset      Amount          Price (USD)     Value (USD)")
            print("-------------------------------------------------------")
            for balance in balances:
                print(f"{balance['asset']:<10} {balance['amount']:<15.8f} ${balance.get('price', 0):<15.2f} ${balance.get('value', 0):<15.2f}")
            total = sum(balance.get('value', 0) for balance in balances)
            print("-------------------------------------------------------")
            print(f"TOTAL                                      ${total:<15.2f}")
        else:
            print("No balances found or an error occurred.")
    else:
        print("Failed to connect to Bitfinex API.") 