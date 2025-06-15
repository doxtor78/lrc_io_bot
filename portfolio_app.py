import sys
import os
import time
import requests
import base64
import hashlib
import hmac
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for
from binance.client import Client
from binance_balances import get_binance_balances
from bybit_balances import get_bybit_balances
import pandas as pd

# Check if running in virtual environment
if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix') or sys.base_prefix == sys.prefix:
    print("ERROR: This script must be run in the virtual environment (venv).")
    print("Please activate the virtual environment first with: source venv/bin/activate")
    sys.exit(1)

app = Flask(__name__)

# Kraken API credentials
KRAKEN_API_KEY = 'lnlMNYd+mD3zRHw0IcBRkBAycn+SOFjhrbSj9yvHXwn3yPiys8BYST47'
KRAKEN_API_SECRET = 'NmvhB+59u58ZDke+nqKD6RU8FxmqWk2VLDpKZCqttIdQ6PrI0ukY86KqHpbLn62jndenrLggVB36q1+ZsCvXMQ=='

# Kraken asset mapping
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

def kraken_request(uri_path, data):
    """Make a request to Kraken private API."""
    url = "https://api.kraken.com" + uri_path
    data['nonce'] = str(int(1000*time.time()))
    postdata = "&".join([f"{k}={v}" for k, v in data.items()])
    encoded = (str(data['nonce']) + postdata).encode()
    message = uri_path.encode() + hashlib.sha256(encoded).digest()
    
    # Use the global KRAKEN_API_SECRET and KRAKEN_API_KEY
    signature = hmac.new(base64.b64decode(KRAKEN_API_SECRET), message, hashlib.sha512)
    sigdigest = base64.b64encode(signature.digest())
    
    headers = {'API-Key': KRAKEN_API_KEY, 'API-Sign': sigdigest.decode()}
    response = requests.post(url, data=data, headers=headers)
    return response.json()

@app.route('/')
def index():
    return redirect(url_for('calculator'))

def custom_round(n):
    """Round to the nearest 100 if > 1000, else to nearest 10."""
    if n > 1000:
        return round(n / 100) * 100
    return round(n / 10) * 10

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    if request.method == 'POST':
        try:
            # --- Phase 1: Read inputs from form ---
            inputs = {k: float(v) if k not in ['trade_side', 'capital_type', 'calculation_type'] else v for k, v in request.form.items()}
            trade_side = inputs.get('trade_side', 'long')
            capital_type = inputs.get('capital_type', 'btc')
            calculation_type = inputs.get('calculation_type', 'symmetric')

            results = {
                'symmetric': {},
                'asymmetric': {}
            }
            
            warning_symmetric = None
            warning_asymmetric = None

            # --- Initial Calculations ---
            entry_1 = inputs['entry_1']
            entry_2 = inputs['entry_2']
            s1, s2 = (max(entry_1, entry_2), min(entry_1, entry_2)) if trade_side == 'long' else (min(entry_1, entry_2), max(entry_1, entry_2))
            step = (s2 - s1) / 4
            entry_levels = [s1 + (step * i) for i in range(5)]
            
            tp1 = inputs['tp1']
            tp5 = inputs['tp5']
            tp_step = (tp5 - tp1) / 4
            tp_levels = [tp1 + (tp_step * i) for i in range(5)]
            average_tp = sum(tp_levels) / len(tp_levels) if tp_levels else 0

            # --- Unified Calculation Loop ---
            for strat in ['symmetric', 'asymmetric']:
                res = results[strat]
                warning_message = None

                # --- Step 1: Calculate Average Entry Price ---
                if strat == 'symmetric':
                    res['avg_entry'] = (s1 + s2) / 2
                else: # asymmetric
                    weights = [5, 1.25, 1.25, 1.25, 1.25]
                    total_weight = sum(weights)
                    res['avg_entry'] = sum(entry_levels[i] * weights[i] for i in range(5)) / total_weight if total_weight != 0 else 0

                # --- Step 2: Common Calculations ---
                if trade_side == 'long':
                    res['sl_distance_pct'] = ((res['avg_entry'] - inputs['sl']) / res['avg_entry']) * 100 if res['avg_entry'] != 0 else 0
                else:  # Short
                    res['sl_distance_pct'] = ((inputs['sl'] - res['avg_entry']) / res['avg_entry']) * 100 if res['avg_entry'] != 0 else 0
                
                res['risk_coefficient'] = abs(res['sl_distance_pct'] / inputs['risk_percentage']) if inputs['risk_percentage'] != 0 else 0

                # --- Step 3: Position Size and Leverage ---
                risk_pct = inputs['risk_percentage'] / 100
                sl_price_diff = abs(res['avg_entry'] - inputs['sl'])
                deployed_capital_percentage = inputs['capital_to_deploy_percentage'] / 100

                if capital_type == 'btc':
                    risk_capital_btc = inputs['total_capital'] * risk_pct
                    res['position_size_btc'] = (risk_capital_btc * res['avg_entry']) / sl_price_diff if sl_price_diff != 0 else 0
                    deployed_capital_btc = inputs['total_capital'] * deployed_capital_percentage
                    res['leverage'] = res['position_size_btc'] / deployed_capital_btc if deployed_capital_btc != 0 else 0
                    res['position_size_usd'] = res['position_size_btc'] * res['avg_entry']
                else:  # usd
                    risk_capital_usd = inputs['total_capital'] * risk_pct
                    required_position_size_btc = risk_capital_usd / sl_price_diff if sl_price_diff != 0 else 0
                    
                    deployed_capital_usd = inputs['total_capital'] * deployed_capital_percentage
                    required_position_size_usd = required_position_size_btc * res['avg_entry']

                    # Spot Market Constraint: Position size cannot exceed deployed capital
                    if required_position_size_usd > deployed_capital_usd:
                        warning_message = "Warning: Required position size for specified risk exceeds deployed capital. Position size has been capped to deployed capital, and leverage set to 1x (spot trade)."
                        res['position_size_usd'] = deployed_capital_usd
                        res['leverage'] = 1.0
                    else:
                        res['position_size_usd'] = required_position_size_usd
                        res['leverage'] = required_position_size_usd / deployed_capital_usd if deployed_capital_usd != 0 else 0
                    
                    # Final BTC position size is derived from the (potentially capped) USD size
                    res['position_size_btc'] = res['position_size_usd'] / res['avg_entry'] if res['avg_entry'] != 0 else 0

                # --- Step 4: Real RR ---
                numerator_rr = abs(average_tp - inputs['sl'])
                denominator_rr = abs(res['avg_entry'] - inputs['sl'])
                res['real_rr'] = numerator_rr / denominator_rr if denominator_rr != 0 else 0

                if strat == 'symmetric':
                    warning_symmetric = warning_message
                else:
                    warning_asymmetric = warning_message

            # --- Phase 3: Entry Order Calculations (Now that position sizes are known) ---
            results['phase3'] = {'symmetric': [], 'asymmetric': []}
            # Symmetric Entries
            sym_pos_size_btc = results['symmetric']['position_size_btc']
            for level in entry_levels:
                volume_coin = sym_pos_size_btc / 5
                results['phase3']['symmetric'].append({
                    'level': level,
                    'volume_usd': volume_coin * level,
                    'volume_coin': volume_coin
                })
            # Asymmetric Entries
            asym_pos_size_btc = results['asymmetric']['position_size_btc']
            for i, level in enumerate(entry_levels):
                volume_coin = asym_pos_size_btc * (weights[i] / 10)
                results['phase3']['asymmetric'].append({
                    'level': level,
                    'volume_usd': volume_coin * level,
                    'volume_coin': volume_coin
                })

            # --- Phases 4, 5, 6 ---
            results['phase4'] = {'symmetric': [], 'asymmetric': []}
            results['phase5'] = {'symmetric': [], 'asymmetric': []}
            results['phase6'] = {'symmetric': [], 'asymmetric': []}
            
            # This is now calculated above from tp1 and tp5
            # tp_levels = [inputs[f'tp{i}'] for i in range(1, 6)] 

            # --- Symmetric ---
            # Phase 4 (Round Entries)
            sym_entry_btc_per_level = results['symmetric']['position_size_btc'] / 5
            for i in range(5):
                original_entry = results['phase3']['symmetric'][i]
                # USD is calculated from the UNROUNDED, equal BTC share, then rounded.
                rounded_usd = custom_round(sym_entry_btc_per_level * original_entry['level'])
                results['phase4']['symmetric'].append({
                    'level': original_entry['level'],
                    'volume_usd': rounded_usd,
                    'volume_coin': sym_entry_btc_per_level # This is now fixed and equal
                })

            sym_pos_size_btc = results['symmetric']['position_size_btc']
            sym_coin_vol_per_tp = sym_pos_size_btc / 5 # Equal BTC share per TP
            for i in range(5): # Loop over 5 TPs for exits
                # Phase 5 (Calculate Exits)
                p5_volume_coin = sym_coin_vol_per_tp
                p5_volume_usd = p5_volume_coin * tp_levels[i]
                results['phase5']['symmetric'].append({
                    'level': tp_levels[i],
                    'volume_usd': p5_volume_usd,
                    'volume_coin': p5_volume_coin
                })

                # Phase 6 (Round Exits)
                # USD is calculated from the UNROUNDED, equal BTC share, then rounded.
                p6_rounded_usd = custom_round(p5_volume_coin * tp_levels[i])
                results['phase6']['symmetric'].append({
                    'level': tp_levels[i],
                    'volume_usd': p6_rounded_usd,
                    'volume_coin': p5_volume_coin # This is now fixed and equal
                })
            
            # --- Asymmetric ---
            # Phase 4 (Round Entries)
            for i in range(5):
                original_entry = results['phase3']['asymmetric'][i]
                rounded_usd = custom_round(original_entry['volume_usd'])
                results['phase4']['asymmetric'].append({
                    'level': original_entry['level'],
                    'volume_usd': rounded_usd,
                    'volume_coin': rounded_usd / original_entry['level'] if original_entry['level'] != 0 else 0
                })

            asym_pos_size_btc = results['asymmetric']['position_size_btc']
            asym_coin_vol_per_tp = asym_pos_size_btc / 5 # Equal BTC share per TP
            for i in range(5): # Loop over 5 TPs for exits
                # Phase 5 (Calculate Exits)
                p5_volume_coin = asym_coin_vol_per_tp
                p5_volume_usd = p5_volume_coin * tp_levels[i]
                results['phase5']['asymmetric'].append({
                    'level': tp_levels[i],
                    'volume_usd': p5_volume_usd,
                    'volume_coin': p5_volume_coin
                })
                
                # Phase 6 (Round Exits)
                p6_rounded_usd = custom_round(p5_volume_coin * tp_levels[i])
                results['phase6']['asymmetric'].append({
                    'level': tp_levels[i],
                    'volume_usd': p6_rounded_usd,
                    'volume_coin': p6_rounded_usd / tp_levels[i] if tp_levels[i] != 0 else 0
                })

            # --- Final Rendering ---
            return render_template('calculator.html', 
                                 results=results, 
                                 inputs=inputs,
                                 warning_symmetric=warning_symmetric,
                                 warning_asymmetric=warning_asymmetric)
        except Exception as e:
            return render_template('calculator.html', error=str(e), inputs=request.form)

    # Initial GET request
    return render_template('calculator.html', inputs={'trade_side': 'long', 'capital_type': 'btc', 'calculation_type': 'symmetric'})

@app.after_request
def add_no_cache_header(response):
    """Add headers to prevent caching."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/api/kraken-balances')
def kraken_balances():
    try:
        # Get balances
        url = 'https://api.kraken.com/0/private/Balance'
        data = {}
        response = kraken_request(url, data)
        if 'error' in response and response['error']:
            print("Kraken API error:", response['error'])
            return jsonify({'success': False, 'error': response['error']})
        if 'result' not in response:
            print("Unexpected Kraken response:", response)
            return jsonify({'success': False, 'error': 'Invalid response from Kraken'})
        # Process balances
        balances = []
        for asset, amount in response['result'].items():
            if float(amount) > 0:
                symbol = KRAKEN_ASSET_MAP.get(asset, asset)
                balances.append({'asset': symbol, 'amount': float(amount)})
        # Get current prices for all assets from Kraken public API
        if balances:
            symbols = [b['asset'] for b in balances]
            # Kraken uses XBT for BTC in pairs
            pairs = [f'{"XBT" if s=="BTC" else s}USD' for s in symbols]
            price_url = 'https://api.kraken.com/0/public/Ticker'
            price_data = {'pair': ','.join(pairs)}
            price_response = requests.get(price_url, params=price_data)
            price_data = price_response.json()
            if 'result' in price_data:
                for balance, pair in zip(balances, pairs):
                    # Kraken may return pair names with prefixes (e.g., XXBTZUSD)
                    found = None
                    for k in price_data['result'].keys():
                        if pair in k:
                            found = k
                            break
                    if found:
                        price = float(price_data['result'][found]['c'][0])
                        balance['price'] = price
                        balance['value'] = balance['amount'] * price
        return jsonify({
            'success': True,
            'balances': balances,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print("Error fetching Kraken balances:", str(e))
        return jsonify({'success': False, 'error': str(e)})

# Your Binance API credentials
API_KEY = '8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7'
API_SECRET = 'jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO'

@app.route('/api/binance-balances')
def api_binance_balances():
    balances = get_binance_balances(API_KEY, API_SECRET)
    return jsonify(balances)

# Your Bybit API credentials
BYBIT_API_KEY = '3hqwkcMjnyhnFUd6XE'
BYBIT_API_SECRET = 'OQVX53FdiY4LMztOZAzYxD3UjS93mFpV3XfK'

@app.route('/api/bybit-balances')
def bybit_balances():
    try:
        balances = get_bybit_balances(BYBIT_API_KEY, BYBIT_API_SECRET)
        return jsonify({
            'success': True,
            'balances': balances,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print("Error fetching Bybit balances:", str(e))
        return jsonify({'success': False, 'error': str(e)})

# --- API Credentials ---
COINMARKETCAP_API_KEY = '2a83a14e-7f99-4dce-ab96-3a0d1f8ddf8b'

# Bitstamp
BITSTAMP_API_KEY = 'jihKE0CWGln3A1mczdKTUoazcfqPnQSb'
BITSTAMP_API_SECRET = 'FNxEXCRiJaEOC6BXmJ7KIvK7imZ6GRKP'
BITSTAMP_CUSTOMER_ID = 'jklv7730'

# Bitfinex
BITFINEX_API_KEY = 'cbb2e86f32e6b4256478f1d38bd8e88d725e6312940'
BITFINEX_API_SECRET = '171522474c91db9e7b144528d6cd82ffc10a4603114'

# BitMEX
BITMEX_API_KEY = 'wZ6_u4IKRmWrwlt0NB8o_ACi'
BITMEX_API_SECRET = '22KthvDICWGThQ3_MAseFwiluDQPZz9yb1uQKaIyTw84EALY'

# --- Asset Symbol Normalization and Filtering ---
ASSET_MAP = {
    # Kraken
    'XBT.F': 'BTC', 'XBT.B': 'BTC', 'XBT': 'BTC', 'XXBT': 'BTC',
    'SOL.S': 'SOL',
    'ZUSD': 'USD', 'USD.F': 'USD',
    'USDT.F': 'USDT',
    # Bybit - ETHF is a distinct asset, do not map to ETH
    # 'ETHF': 'ETH', 
    # Binance
    'LDBNB': 'BNB', 'LDUSDT': 'USDT', 'LDCAKE': 'CAKE', 'LDO': 'LDO',
    'NFT': 'APENFT',
    # Bitstamp
    'ETH2': 'ETH',
    # BitMEX
    'XBT': 'BTC'
}

# Symbols to ignore during price fetching because they are delisted or not on CMC
IGNORE_LIST = {'ADD', 'ANC', 'ATD', 'EON', 'EOP', 'JEX', 'MEETONE', 'ETHF', 'SOL.S', 'USD.F', 'USDT.F', 'XBT.B', 'XBT.F'}

# --- Exchange Request Functions ---
def bybit_request(endpoint, params=None):
    url = f'https://api.bybit.com/v5/{endpoint}'
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())]) if params else ""
    string_to_sign = timestamp + BYBIT_API_KEY + recv_window + query_string
    signature = hmac.new(BYBIT_API_SECRET.encode('utf-8'), msg=string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
    headers = {'X-BAPI-API-KEY': BYBIT_API_KEY, 'X-BAPI-TIMESTAMP': timestamp, 'X-BAPI-RECV-WINDOW': recv_window, 'X-BAPI-SIGN': signature}
    return requests.get(url, headers=headers, params=params).json()

def binance_request(endpoint, params={}):
    url = f'https://api.binance.com{endpoint}'
    params['timestamp'] = int(time.time() * 1000)
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature
    headers = {'X-MBX-APIKEY': API_KEY}
    return requests.get(url, headers=headers, params=params).json()

def bitstamp_request(endpoint, params=None):
    url = f'https://www.bitstamp.net/api/v2/{endpoint}/'
    nonce = str(int(time.time() * 1000))
    message = nonce + BITSTAMP_CUSTOMER_ID + BITSTAMP_API_KEY
    signature = hmac.new(BITSTAMP_API_SECRET.encode('utf-8'), msg=message.encode('utf-8'), digestmod=hashlib.sha256).hexdigest().upper()
    data = {'key': BITSTAMP_API_KEY, 'signature': signature, 'nonce': nonce}
    if params: data.update(params)
    return requests.post(url, data=data).json()

def bitfinex_private_request(endpoint, params={}):
    url = f'https://api.bitfinex.com/v1/{endpoint}'
    payload = {'request': f'/v1/{endpoint}', 'nonce': str(int(time.time() * 1000))}
    payload.update(params)
    payload_base64 = base64.b64encode(json.dumps(payload).encode('utf-8'))
    signature = hmac.new(BITFINEX_API_SECRET.encode('utf-8'), payload_base64, hashlib.sha384).hexdigest()
    headers = {'X-BFX-APIKEY': BITFINEX_API_KEY, 'X-BFX-PAYLOAD': payload_base64, 'X-BFX-SIGNATURE': signature}
    return requests.post(url, headers=headers).json()

def bitmex_request(verb, endpoint, params=None):
    """Make a request to the BitMEX API."""
    base_url = "https://www.bitmex.com"
    full_path = "/api/v1" + endpoint
    expires = int(time.time()) + 60
    
    request_data_str = ""
    if verb == 'GET' and params:
        full_path += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

    message = verb + full_path + str(expires) + request_data_str
    signature = hmac.new(BITMEX_API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

    headers = {
        'api-expires': str(expires),
        'api-key': BITMEX_API_KEY,
        'api-signature': signature,
        'Content-Type': 'application/json', 'Accept': 'application/json'
    }

    response = requests.get(base_url + full_path, headers=headers)
    return response.json()

# --- Balance Fetching Functions ---
def get_balances():
    portfolio = []
    # Bybit
    for acc_type in ['UNIFIED', 'FUND']:
        response = bybit_request('account/wallet-balance', {'accountType': acc_type})
        if response and response.get('retCode') == 0:
            for item in response.get('result', {}).get('list', []):
                for coin in item.get('coin', []):
                    if float(coin.get('walletBalance', 0)) > 0:
                        portfolio.append({'exchange': 'Bybit', 'asset': coin['coin'], 'amount': float(coin['walletBalance'])})
    # Binance
    print("--- Fetching Binance Balances ---")
    response = binance_request('/api/v3/account')
    print(f"--- Raw Binance Response ---\n{response}\n--------------------")
    if 'balances' in response:
        for balance in response['balances']:
            if float(balance['free']) + float(balance['locked']) > 0:
                portfolio.append({'exchange': 'Binance', 'asset': balance['asset'], 'amount': float(balance['free']) + float(balance['locked'])})
    # Kraken
    response = kraken_request('/0/private/Balance', {})
    print(f"--- Raw Kraken Response ---\n{response}\n--------------------") # DEBUG
    if response and not response.get('error'):
        for asset, amount in response.get('result', {}).items():
            if float(amount) > 0:
                portfolio.append({'exchange': 'Kraken', 'asset': asset, 'amount': float(amount)})
    # Bitstamp
    response = bitstamp_request('balance')
    if response and 'error' not in response:
        for k, v in response.items():
            if k.endswith('_balance') and float(v) > 0:
                portfolio.append({'exchange': 'Bitstamp', 'asset': k.replace('_balance', '').upper(), 'amount': float(v)})
    # Bitfinex
    response = bitfinex_private_request('balances')
    if isinstance(response, list):
        for balance in response:
            if balance.get('type') == 'exchange' and float(balance.get('amount', 0)) > 0:
                portfolio.append({'exchange': 'Bitfinex', 'asset': balance['currency'].upper(), 'amount': float(balance['amount'])})
    
    # BitMEX
    print("--- Fetching BitMEX Balances ---")
    response = bitmex_request('GET', '/user/walletSummary')
    print(f"--- Raw BitMEX Response ---\n{response}\n--------------------")
    if isinstance(response, list):
        for wallet in response:
            # Only use the 'Total' balance summary to avoid duplicates and get the correct total amount.
            if wallet.get('transactType') == 'Total':
                balance = wallet.get('walletBalance', 0)
                if balance > 0:
                    asset = wallet['currency'].upper()
                    # BitMEX returns XBT in Satoshis. 1 BTC = 100,000,000 Satoshis.
                    if asset == 'XBT':
                        balance = balance / 100000000.0
                    
                    portfolio.append({'exchange': 'BitMEX', 'asset': asset, 'amount': balance})

    return portfolio

def get_prices(symbols):
    """Fetch prices from CoinMarketCap API with improved error handling and logging."""
    if not symbols:
        return {}
    
    headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
    # CMC API requires uppercase, comma-separated symbols
    params = {'symbol': ','.join(set(s.upper() for s in symbols))}
    
    print(f"--- Fetching prices for symbols: {params['symbol']} ---")
    
    try:
        response = requests.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest', headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        response_json = response.json()
        
        print(f"--- CoinMarketCap API Response (Status: {response.status_code}) ---")

        prices = {}
        if response_json.get('status', {}).get('error_code') == 0 and 'data' in response_json:
            data = response_json['data']
            for symbol_upper in data:
                # Handle cases where CMC returns a list for a symbol (e.g., name conflicts)
                item = data[symbol_upper][0] if isinstance(data[symbol_upper], list) else data[symbol_upper]
                price = item['quote']['USD']['price']
                
                # Find original, case-sensitive symbols that match the uppercase symbol
                for original_symbol in symbols:
                    if original_symbol.upper() == symbol_upper:
                        prices[original_symbol] = price
        else:
            print(f"CoinMarketCap API Error: {response_json.get('status', {}).get('error_message')}")

        print(f"--- Parsed Prices ---\n{prices}\n--------------------")
        return prices
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling CoinMarketCap API: {e}")
        return {}

if __name__ == '__main__':
    app.run(debug=True, port=5006)