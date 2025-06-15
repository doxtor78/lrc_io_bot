import requests
import hmac
import hashlib
import time
import json
import base64
from datetime import datetime

# Bybit API credentials
BYBIT_API_KEY = '3hqwkcMjnyhnFUd6XE'
BYBIT_API_SECRET = 'OQVX53FdiY4LMztOZAzYxD3UjS93mFpV3XfK'

# Binance API credentials
BINANCE_API_KEY = '8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7'
BINANCE_API_SECRET = 'jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO'

# Kraken API credentials
KRAKEN_API_KEY = 'lnlMNYd+mD3zRHw0IcBRkBAycn+SOFjhrbSj9yvHXwn3yPiys8BYST47'
KRAKEN_API_SECRET = 'NmvhB+59u58ZDke+nqKD6RU8FxmqWk2VLDpKZCqttIdQ6PrI0ukY86KqHpbLn62jndenrLggVB36q1+ZsCvXMQ=='

# Bitstamp API credentials
BITSTAMP_API_KEY = 'jihKE0CWGln3A1mczdKTUoazcfqPnQSb'
BITSTAMP_API_SECRET = 'FNxEXCRiJaEOC6BXmJ7KIvK7imZ6GRKP'
BITSTAMP_CUSTOMER_ID = 'jklv7730'

# Bitfinex API credentials
BITFINEX_API_KEY = 'cbb2e86f32e6b4256478f1d38bd8e88d725e6312940'
BITFINEX_API_SECRET = '171522474c91db9e7b144528d6cd82ffc10a4603114'

def bybit_request(endpoint, params=None):
    """Make a request to Bybit v5 API."""
    url = f'https://api.bybit.com/v5/{endpoint}'
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    
    query_string = ""
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])

    string_to_sign = timestamp + BYBIT_API_KEY + recv_window + query_string
    signature = hmac.new(BYBIT_API_SECRET.encode('utf-8'), msg=string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
    
    headers = {
        'X-BAPI-API-KEY': BYBIT_API_KEY,
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-RECV-WINDOW': recv_window,
        'X-BAPI-SIGN': signature,
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def binance_request(endpoint, params={}):
    """Make a request to Binance API."""
    url = f'https://api.binance.com{endpoint}'
    params['timestamp'] = int(time.time() * 1000)
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(BINANCE_API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature
    headers = {'X-MBX-APIKEY': BINANCE_API_KEY}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def kraken_request(uri_path, data):
    """Make a request to Kraken private API."""
    url = "https://api.kraken.com" + uri_path
    data['nonce'] = str(int(1000*time.time()))
    postdata = "&".join([f"{k}={v}" for k, v in data.items()])
    encoded = (str(data['nonce']) + postdata).encode()
    message = uri_path.encode() + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(KRAKEN_API_SECRET), message, hashlib.sha512)
    sigdigest = base64.b64encode(signature.digest())
    headers = {'API-Key': KRAKEN_API_KEY, 'API-Sign': sigdigest.decode()}
    response = requests.post(url, data=data, headers=headers)
    return response.json()

def bitstamp_request(endpoint, params=None):
    """Make a request to Bitstamp API."""
    url = f'https://www.bitstamp.net/api/v2/{endpoint}/'
    nonce = str(int(time.time() * 1000))
    message = nonce + BITSTAMP_CUSTOMER_ID + BITSTAMP_API_KEY
    signature = hmac.new(BITSTAMP_API_SECRET.encode('utf-8'), msg=message.encode('utf-8'), digestmod=hashlib.sha256).hexdigest().upper()
    data = {'key': BITSTAMP_API_KEY, 'signature': signature, 'nonce': nonce}
    if params:
        data.update(params)
    response = requests.post(url, data=data)
    return response.json()

def bitfinex_private_request(endpoint, params={}):
    """Make a request to Bitfinex private API."""
    url = f'https://api.bitfinex.com/v1/{endpoint}'
    payload = {'request': f'/v1/{endpoint}', 'nonce': str(int(time.time() * 1000))}
    payload.update(params)
    
    payload_json = json.dumps(payload)
    payload_base64 = base64.b64encode(payload_json.encode('utf-8'))
    
    signature = hmac.new(BITFINEX_API_SECRET.encode('utf-8'), payload_base64, hashlib.sha384).hexdigest()
    headers = {
        'X-BFX-APIKEY': BITFINEX_API_KEY,
        'X-BFX-PAYLOAD': payload_base64,
        'X-BFX-SIGNATURE': signature
    }
    response = requests.post(url, headers=headers)
    return response.json()

def get_bybit_balances():
    balances = []
    account_types = ['UNIFIED', 'FUND']

    for acc_type in account_types:
        try:
            response = bybit_request('account/wallet-balance', {'accountType': acc_type})
            if response and response.get('retCode') == 0:
                for item in response.get('result', {}).get('list', []):
                    for coin in item.get('coin', []):
                        balance = float(coin.get('walletBalance', 0))
                        if balance > 0:
                            asset_name = f"{coin['coin']} ({acc_type})"
                            balances.append({'asset': asset_name, 'amount': balance})
        except Exception as e:
            print(f"Could not fetch Bybit {acc_type} balances: {e}")
    return balances

def get_binance_balances():
    """Fetch Binance account balances."""
    response = binance_request('/api/v3/account')
    if 'balances' in response:
        balances = []
        for balance in response['balances']:
            amount = float(balance['free']) + float(balance['locked'])
            if amount > 0:
                balances.append({
                    'asset': balance['asset'],
                    'amount': amount,
                })
        return balances
    return []

def get_kraken_balances():
    """Fetch Kraken account balances."""
    response = kraken_request('/0/private/Balance', {})
    if 'result' in response:
        balances = []
        for asset, amount in response['result'].items():
            if float(amount) > 0:
                balances.append({
                    'asset': asset,
                    'amount': float(amount),
                })
        return balances
    return []

def get_bitstamp_balances():
    """Fetch Bitstamp account balances."""
    response = bitstamp_request('balance')
    if 'error' not in response:
        balances = []
        for asset_field, amount_str in response.items():
            if asset_field.endswith('_balance'):
                asset = asset_field.replace('_balance', '').upper()
                amount = float(amount_str)
                if amount > 0:
                    balances.append({
                        'asset': asset,
                        'amount': amount,
                    })
        return balances
    return []

def get_bitfinex_balances():
    """Fetch Bitfinex account balances."""
    response = bitfinex_private_request('balances')
    if isinstance(response, list):
        balances = []
        for balance in response:
            if balance.get('type') == 'exchange' and float(balance.get('amount', 0)) > 0:
                balances.append({
                    'asset': balance['currency'].upper(),
                    'amount': float(balance['amount']),
                })
        return balances
    return []

def fetch_all_balances():
    """Fetch balances from all exchanges and display them."""
    print("Fetching balances from all exchanges...")
    bybit_balances = get_bybit_balances()
    binance_balances = get_binance_balances()
    kraken_balances = get_kraken_balances()
    bitstamp_balances = get_bitstamp_balances()
    bitfinex_balances = get_bitfinex_balances()

    print("\nBybit Balances:")
    for balance in bybit_balances:
        print(f"{balance['asset']}: {balance['amount']}")

    print("\nBinance Balances:")
    for balance in binance_balances:
        print(f"{balance['asset']}: {balance['amount']}")

    print("\nKraken Balances:")
    for balance in kraken_balances:
        print(f"{balance['asset']}: {balance['amount']}")

    print("\nBitstamp Balances:")
    for balance in bitstamp_balances:
        print(f"{balance['asset']}: {balance['amount']}")

    print("\nBitfinex Balances:")
    for balance in bitfinex_balances:
        print(f"{balance['asset']}: {balance['amount']}")

if __name__ == '__main__':
    fetch_all_balances() 