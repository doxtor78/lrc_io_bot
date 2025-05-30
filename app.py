import sys
import os

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
import time
import sqlite3
from playwright.sync_api import sync_playwright
import logging

app = Flask(__name__)

# BitMEX Testnet REST API base URL
BITMEX_API = "https://www.bitmex.com/api/v1/"

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

# Dashboard route
@app.route('/')
def dashboard():
    print("Serving dashboard at", datetime.now().isoformat())
    return render_template('index.html')

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

if __name__ == '__main__':
    # Clean the database: remove non-BTC data
    conn = sqlite3.connect("funding_rates.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM funding_rates WHERE UPPER(symbol) NOT LIKE 'BTC%' AND UPPER(symbol) NOT LIKE 'XBT%'")
    conn.commit()
    conn.close()
    app.run(debug=True, port=5003)