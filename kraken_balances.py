import time
import requests
import base64
import hashlib
import hmac

KRAKEN_API_KEY = 'lnlMNYd+mD3zRHw0IcBRkBAycn+SOFjhrbSj9yvHXwn3yPiys8BYST47'
KRAKEN_API_SECRET = 'NmvhB+59u58ZDke+nqKD6RU8FxmqWk2VLDpKZCqttIdQ6PrI0ukY86KqHpbLn62jndenrLggVB36q1+ZsCvXMQ=='

KRAKEN_ASSET_MAP = {
    'XBT': 'BTC',
    'XETH': 'ETH',
    'ZEUR': 'EUR',
    'ZUSD': 'USD',
    'USDT': 'USDT',
    'DOT': 'DOT',
    'ADA': 'ADA',
    'SOL': 'SOL',
    'MATIC': 'MATIC',
    'LINK': 'LINK',
    'UNI': 'UNI',
    'AAVE': 'AAVE',
    'ALGO': 'ALGO',
    'ATOM': 'ATOM',
    'AVAX': 'AVAX',
    'BCH': 'BCH',
    'DASH': 'DASH',
    'EOS': 'EOS',
    'LTC': 'LTC',
    'XRP': 'XRP',
    'XTZ': 'XTZ',
    'YFI': 'YFI',
    'ZEC': 'ZEC'
}

def get_kraken_nonce():
    return str(int(time.time() * 1000))

def kraken_request(url, data, api_key, api_secret):
    nonce = get_kraken_nonce()
    data['nonce'] = nonce
    post_data = '&'.join([f'{k}={v}' for k, v in data.items()])
    path = url.split('kraken.com')[1]
    secret = base64.b64decode(api_secret)
    hash_digest = hashlib.sha256((nonce + post_data).encode()).digest()
    hmac_digest = hmac.new(secret, (path.encode() + hash_digest), hashlib.sha512).digest()
    signature = base64.b64encode(hmac_digest)
    headers = {
        'API-Key': api_key,
        'API-Sign': signature.decode(),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    response = requests.post(url, data=data, headers=headers)
    return response.json()

def get_kraken_asset_pairs():
    """Fetch Kraken asset pairs and build a mapping from (base, quote) to Kraken pair code."""
    url = 'https://api.kraken.com/0/public/AssetPairs'
    response = requests.get(url)
    data = response.json()
    mapping = {}
    if 'result' in data:
        for pair_code, info in data['result'].items():
            base = info['base']
            quote = info['quote']
            mapping[(base, quote)] = pair_code
    return mapping

def get_kraken_balances():
    url = 'https://api.kraken.com/0/private/Balance'
    data = {}
    response = kraken_request(url, data, KRAKEN_API_KEY, KRAKEN_API_SECRET)
    print("Kraken Balance API Response:", response)
    if 'error' in response and response['error']:
        print("Kraken API error:", response['error'])
        return []
    if 'result' not in response:
        print("Unexpected Kraken response:", response)
        return []
    balances = []
    btc_reserve = 0.0
    btc_codes = ['XBT.F', 'XBT.M']
    btc_amounts = {}
    for asset, amount in response['result'].items():
        if float(amount) > 0:
            symbol = KRAKEN_ASSET_MAP.get(asset, asset)
            if asset in btc_codes:
                btc_reserve += float(amount)
                btc_amounts[asset] = float(amount)
            else:
                balances.append({'asset': symbol, 'kraken_code': asset, 'amount': float(amount)})
    # Add combined BTC reserve
    if btc_reserve > 0:
        balances.insert(0, {'asset': 'BTC (XBT.F+XBT.M)', 'kraken_code': 'XBT.F', 'amount': btc_reserve, 'btc_breakdown': btc_amounts})
    # Get current prices for all assets from Kraken public API
    if balances:
        asset_pairs = get_kraken_asset_pairs()
        pairs = []
        pair_map = {}
        for b in balances:
            base = b['kraken_code']
            quote = 'ZUSD'  # Kraken's code for USD
            pair_code = asset_pairs.get((base, quote))
            # For combined BTC, try XBT.FZUSD, then XBT.MZUSD
            if b['asset'] == 'BTC (XBT.F+XBT.M)':
                pair_code = asset_pairs.get(('XBT.F', 'ZUSD')) or asset_pairs.get(('XBT.M', 'ZUSD'))
            if pair_code:
                pairs.append(pair_code)
                pair_map[pair_code] = b
        if pairs:
            price_url = 'https://api.kraken.com/0/public/Ticker'
            price_data = {'pair': ','.join(pairs)}
            price_response = requests.get(price_url, params=price_data)
            price_data = price_response.json()
            print("Kraken Price API Response:", price_data)
            if 'result' in price_data:
                for pair_code in pairs:
                    balance = pair_map[pair_code]
                    if pair_code in price_data['result']:
                        price = float(price_data['result'][pair_code]['c'][0])
                        balance['price'] = price
                        balance['value'] = balance['amount'] * price
                    else:
                        print(f"No price found for pair {pair_code}")
            else:
                print("No price data found in response.")
        else:
            print("No valid asset pairs found for price lookup.")
    return balances

if __name__ == '__main__':
    balances = get_kraken_balances()
    if not balances:
        print("No assets found on Kraken.")
    else:
        # Sort by asset name
        balances.sort(key=lambda x: x['asset'])
        print(f"{'Asset':<10} {'Amount':<15} {'Price (USD)':<15} {'Value (USD)':<15}")
        print("-" * 55)
        for b in balances:
            price = b.get('price', 0)
            value = b.get('value', 0)
            print(f"{b['asset']:<10} {b['amount']:<15.8f} ${price:<14.2f} ${value:<14.2f}")
        print("-" * 55)
        total = sum(b.get('value', 0) for b in balances)
        print(f"{'TOTAL':<10} {'':<15} {'':<15} ${total:<14.2f}") 