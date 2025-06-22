import sys
import os
import time
import requests
import ccxt
import json

# Check if running in virtual environment
if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix') or sys.base_prefix == sys.prefix:
    print("ERROR: This script must be run in the virtual environment (venv).")
    print("Please activate the virtual environment first with: source venv/bin/activate")
    sys.exit(1)

from flask import Flask, render_template, jsonify, request
import requests
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
import funding_rates
import threading
import sqlite3
from playwright.sync_api import sync_playwright
import logging
from lrc_calculator import calculate_lrc_parameters

app = Flask(__name__)

# --- Cache Busting ---
# Ensure templates are auto-reloaded and not cached by the browser
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    """Add headers to force latest content and prevent caching."""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# --- Binance API Credentials (with security warning) ---
# For your security, please REVOKE these keys from your Binance account after this session.
# In real applications, use environment variables.
BINANCE_API_KEY = "8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7"
BINANCE_SECRET_KEY = "jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO"

# BitMEX Testnet REST API base URL
BITMEX_API = "https://testnet.bitmex.com/api/v1/"

# Kraken API credentials
KRAKEN_API_KEY = os.environ.get('KRAKEN_API_KEY', 'YOUR_KRAKEN_API_KEY')
KRAKEN_API_SECRET = os.environ.get('KRAKEN_API_SECRET', 'YOUR_KRAKEN_API_SECRET')

def background_funding_scraper():
    while True:
        try:
            conn = funding_rates.init_db(check_same_thread=False)
            funding_data = funding_rates.scrape_funding_rates()
            funding_rates.save_to_db(conn, funding_data)
            conn.close()
            print(f"Updated funding rates at {datetime.now().isoformat()}")
            print(f"Scraped {len(funding_data)} funding rate rows.", flush=True)
        except Exception as e:
            print(f"Error updating funding rates: {str(e)}")
        time.sleep(8 * 60 * 60)  # Sleep for 8 hours

# Start background scraper
scraper_thread = threading.Thread(target=background_funding_scraper, daemon=True)
scraper_thread.start()

# Fetch historical candlestick data
@app.route('/historical-data')
def get_historical_data():
    print("Starting /historical-data request at", datetime.now().isoformat())
    try:
        # Get binSize from query params, default to '1m'
        bin_size = request.args.get('binSize', '1m')
        params = {
            'symbol': 'XBTUSD',
            'binSize': bin_size,
            'count': 1000,
            'reverse': True
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        print("Fetching BitMEX API with params:", params)
        response = requests.get(f"{BITMEX_API}trade/bucketed", params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        print("BitMEX response: %d candles" % len(data))

        # Aggregate all candles per minute
        candle_agg = defaultdict(list)
        for bar in data:
            ts = int(datetime.strptime(bar['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp())
            candle_agg[ts].append(bar)

        formatted_data = []
        for ts in sorted(candle_agg.keys()):
            bars = candle_agg[ts]
            open_ = float(bars[0]['open'])
            close_ = float(bars[-1]['close'])
            high_ = max(float(bar['high']) for bar in bars)
            low_ = min(float(bar['low']) for bar in bars)
            volume_ = sum(float(bar['volume']) for bar in bars)
            formatted_data.append({
                'time': ts,
                'open': open_,
                'high': high_,
                'low': low_,
                'close': close_,
                'volume': volume_
            })
        print("Formatted data sample:", formatted_data[:2])
        return jsonify(formatted_data)
    except Exception as e:
        print("BitMEX API error:", str(e))
        if 'response' in locals():
            print("Response content:", response.content)
        # Static fallback data
        fallback_data = [
            {"time": int((datetime.now() - timedelta(minutes=5)).timestamp()), "open": 60000, "high": 60010, "low": 59990, "close": 60005, "volume": 1000},
            {"time": int((datetime.now() - timedelta(minutes=4)).timestamp()), "open": 60005, "high": 60015, "low": 59995, "close": 60010, "volume": 1100},
            {"time": int((datetime.now() - timedelta(minutes=3)).timestamp()), "open": 60010, "high": 60020, "low": 60000, "close": 60015, "volume": 1200},
            {"time": int((datetime.now() - timedelta(minutes=2)).timestamp()), "open": 60015, "high": 60025, "low": 60005, "close": 60020, "volume": 1300},
            {"time": int((datetime.now() - timedelta(minutes=1)).timestamp()), "open": 60020, "high": 60030, "low": 60010, "close": 60025, "volume": 1400}
        ]
        print("Fallback data on error:", fallback_data)
        return jsonify(fallback_data)

def _fetch_all_candles_since(exchange, symbol, timeframe, start_timestamp_sec):
    """Fetches all candles from a start date by paginating through the API."""
    since_ms = start_timestamp_sec * 1000
    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    
    all_ohlcv = []
    
    while True:
        # Safety check: do not try to fetch data from the future.
        if since_ms > exchange.milliseconds():
            break

        print(f"Fetching {symbol} {timeframe} candles since {datetime.fromtimestamp(since_ms/1000).isoformat()}...")
        # We use a limit of 500, a common and safe number for many exchanges.
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=500)
        
        if not ohlcv:
            break
            
        all_ohlcv.extend(ohlcv)
        
        # If the exchange returns fewer candles than the limit, we've reached the end of the available data.
        if len(ohlcv) < 500:
            break
            
        # The 'since' for the next fetch should be the timestamp of the last candle we received.
        since_ms = ohlcv[-1][0] + timeframe_ms
        
        # Be polite to the API to avoid being rate-limited.
        time.sleep(exchange.rateLimit / 1000)

    # In case of any overlap, filter for unique candles and sort them.
    unique_candles = {c[0]: c for c in all_ohlcv}
    return sorted(unique_candles.values(), key=lambda x: x[0])

@app.route('/api/lrc-data')
def get_lrc_data():
    try:
        # --- 1. Get parameters and instantiate exchange ---
        bin_size = request.args.get('binSize', '1h')
        use_date_range = request.args.get('useDateRange', 'false').lower() == 'true'
        
        # Timestamp for the start of the data fetch for the entire chart
        fetch_start_timestamp = request.args.get('startTimestamp', type=int)
        
        # Timestamp for the inflection point where the LRC calculation begins
        inflection_timestamp = request.args.get('inflectionTimestamp', type=int)

        if not fetch_start_timestamp:
            # As a fallback, default to 90 days ago if no specific start date is given.
            fallback_date = datetime.now() - timedelta(days=90)
            fetch_start_timestamp = int(fallback_date.timestamp())

        # If no inflection point is passed, default it to the fetch start time
        if not inflection_timestamp:
            inflection_timestamp = fetch_start_timestamp

        exchange = ccxt.bitmex({
            'enableRateLimit': True,
        })
        exchange.set_sandbox_mode(True) # Use the official method for testnet
        
        # --- 2. Fetch all data since the start date ---
        ohlcv = _fetch_all_candles_since(exchange, 'XBTUSD', bin_size, fetch_start_timestamp)
        
        if not ohlcv:
            return jsonify({'error': 'No data found for the specified date range.'}), 404

        candles = [{
            'time': int(bar[0] / 1000), # ms to s
            'open': float(bar[1]),
            'high': float(bar[2]),
            'low': float(bar[3]),
            'close': float(bar[4])
        } for bar in ohlcv]

        # --- 3. Get deviation multipliers from request, e.g., "1,2,3,4"
        deviations_str = request.args.get('deviations', '1,2,3,4')
        try:
            deviations = [float(d) for d in deviations_str.split(',')]
        except ValueError:
            return jsonify({"error": "Invalid deviations format. Use comma-separated numbers."}), 400

        # --- 4. Calculate LRC ---
        lrc_params = calculate_lrc_parameters(candles, use_date_range=use_date_range, start_timestamp=inflection_timestamp)

        if not lrc_params:
            return jsonify({"candles": candles, "lrc": None})

        # --- 5. Structure the response ---
        lrc_data = {
            'params': lrc_params,
            'deviations': deviations,
            'timeframe': bin_size
        }

        # --- 6. Save LRC params for the bot ---
        try:
            with open('stable_v3/lrc_params.json', 'w') as f:
                json.dump(lrc_data, f, indent=4)
            app.logger.info("Successfully saved LRC parameters to lrc_params.json")
        except Exception as e:
            app.logger.error(f"Error saving LRC parameters to file: {e}")

        return jsonify({"candles": candles, "lrc": lrc_data})

    except Exception as e:
        app.logger.error(f"Error in /api/lrc-data: {e}")
        return jsonify({'error': str(e)}), 500

# Dashboard route
@app.route('/')
def dashboard():
    print("Serving dashboard at", datetime.now().isoformat())
    return render_template('index.html')

@app.route('/lrc')
def lrc_chart_page():
    """Serves the dedicated LRC chart page."""
    return render_template('lrc_chart.html')

@app.route('/funding-rates/latest')
def get_latest_funding_rates():
    try:
        limit = request.args.get('limit', default=100, type=int)
        conn = funding_rates.init_db()
        rates = funding_rates.get_latest_funding_rates(conn, limit)
        conn.close()
        return jsonify([{
            'timestamp': r[0],
            'symbol': r[1],
            'exchange': r[2],
            'rate': r[3]
        } for r in rates])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/funding-rates/historical')
def get_historical_funding_rates():
    try:
        symbol = request.args.get('symbol', default='BTC')
        exchange = request.args.get('exchange', default='Binance')
        days = request.args.get('days', default=7, type=int)
        conn = funding_rates.init_db()
        rates = funding_rates.get_historical_funding_rates(conn, symbol, exchange, days)
        conn.close()
        return jsonify([{
            'timestamp': r[0],
            'rate': r[1]
        } for r in rates])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/funding-rates/update')
def update_funding_rates():
    print(">>> /funding-rates/update CALLED <<<", flush=True)
    try:
        funding_data = funding_rates.scrape_funding_rates()
        conn = funding_rates.init_db()
        funding_rates.save_to_db(conn, funding_data)
        conn.close()
        return jsonify({'message': f'Successfully updated {len(funding_data)} funding rates'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/funding-rates/matrix')
def get_funding_rates_matrix():
    try:
        conn = funding_rates.init_db()
        cur = conn.cursor()
        
        # Get the latest funding rates for each exchange
        cur.execute('''
            WITH latest_rates AS (
                SELECT 
                    exchange,
                    symbol,
                    rate,
                    price,
                    margin_type,
                    timestamp,
                    ROW_NUMBER() OVER (PARTITION BY exchange ORDER BY timestamp DESC) as rn
                FROM funding_rates
                WHERE symbol = 'BTC'
            )
            SELECT 
                margin_type,
                exchange,
                rate,
                price,
                timestamp
            FROM latest_rates
            WHERE rn = 1
            ORDER BY margin_type, exchange
        ''')
        
        rows = cur.fetchall()
        conn.close()
        
        # Format the response
        matrix = {}
        for margin_type, exchange, rate, price, timestamp in rows:
            if margin_type not in matrix:
                matrix[margin_type] = {}
            matrix[margin_type][exchange] = {
                "rate": float(rate),
                "price": float(price),
                "timestamp": timestamp
            }
            
        return jsonify(matrix)
    except Exception as e:
        logging.error(f"Error in get_funding_rates_matrix: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/coingecko-prices')
def coingecko_prices():
    ids = request.args.get('ids', '')
    vs_currencies = request.args.get('vs_currencies', 'usd')
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies={vs_currencies}'
    print("Proxying to CoinGecko URL:", url)  # Debug print
    try:
        resp = requests.get(url, timeout=10)
        print("CoinGecko response:", resp.text)  # Debug print
        return jsonify(resp.json())
    except Exception as e:
        print("CoinGecko error:", str(e))  # Debug print
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    # Clean the database: remove non-BTC data
    conn = sqlite3.connect("funding_rates.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM funding_rates WHERE UPPER(symbol) NOT LIKE 'BTC%' AND UPPER(symbol) NOT LIKE 'XBT%'")
    conn.commit()
    conn.close()
    # Running with use_reloader=False to prevent zombie processes from locking the port.
    app.run(debug=True, use_reloader=False, port=5004)