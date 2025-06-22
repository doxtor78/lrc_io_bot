from flask import Flask, jsonify, render_template, request
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import BITMEX_TESTNET_API_KEY, BITMEX_TESTNET_API_SECRET

app = Flask(__name__)

# --- LRC Calculation Logic ---
def calculate_lrc_parameters_for_api(data, use_date_range=False, start_timestamp=None, inflection_timestamp=None):
    if not data:
        return {}

    # 1. Get the full data range from the start date forward.
    full_data = data
    if use_date_range and start_timestamp:
        full_data = [d for d in data if d['time'] >= start_timestamp]

    if len(full_data) < 2:
        return {}

    # --- Determine calculation and drawing ranges ---
    is_projection = use_date_range and inflection_timestamp and inflection_timestamp > start_timestamp

    calc_data = full_data
    draw_start_index = 0
    draw_end_index = len(full_data) - 1

    if is_projection:
        try:
            # For projections, calculation data ends at the inflection point
            inflection_bar_index = next(i for i, d in enumerate(full_data) if d['time'] >= inflection_timestamp)
            calc_data = full_data[:inflection_bar_index + 1]
            # And drawing starts from the inflection point
            draw_start_index = inflection_bar_index
        except StopIteration:
            # Inflection point is out of bounds, so this is no longer a projection.
            pass

    if len(calc_data) < 2:
        return {}
        
    # 3. Perform regression on the calculation data.
    calc_indices = np.arange(len(calc_data))
    calc_prices = np.array([d['close'] for d in calc_data])
    
    slope, intercept = np.polyfit(calc_indices, calc_prices, 1)
    std_dev = np.std(calc_prices - (slope * calc_indices + intercept))

    # 4. Project the price to the drawing start and end points
    # The indices of our regression are relative to the start of `full_data`.
    draw_start_price = slope * draw_start_index + intercept
    draw_end_price = slope * draw_end_index + intercept

    draw_start_time = full_data[draw_start_index]['time']
    draw_end_time = full_data[draw_end_index]['time']

    return {
        'start_time': draw_start_time,
        'start_price': draw_start_price,
        'end_time': draw_end_time,
        'end_price': draw_end_price,
        'std_dev': std_dev,
        'slope': slope,
        'intercept': intercept
    }

# --- Exchange Connection ---
def initialize_exchange():
    exchange = ccxt.bitmex({
        'apiKey': BITMEX_TESTNET_API_KEY,
        'secret': BITMEX_TESTNET_API_SECRET,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True)
    return exchange

@app.route('/')
def index():
    """Renders the main chart page."""
    return render_template('index.html')

@app.route('/api/lrc-data')
def get_lrc_data():
    """Provides OHLCV and LRC data to the frontend chart."""
    try:
        # --- Get parameters from request ---
        bin_size = request.args.get('binSize', '1h')
        use_date = request.args.get('useDateRange', 'false').lower() == 'true'
        start_ts = int(request.args.get('startTimestamp', 0))
        inflection_ts = int(request.args.get('inflectionTimestamp', 0))
        deviations_str = request.args.get('deviations', '1,2')
        deviations = [float(d) for d in deviations_str.split(',')]

        # --- Fetch data from exchange ---
        exchange = initialize_exchange()
        limit = 750 
        since = int((datetime.now() - timedelta(days=limit / (24 if bin_size.endswith('h') else 1440))).timestamp() * 1000)
        
        ohlcv = exchange.fetch_ohlcv('XBTUSD', bin_size, since=since, limit=limit)
        
        candles = [
            {'time': t / 1000, 'open': o, 'high': h, 'low': l, 'close': c}
            for t, o, h, l, c, v in ohlcv
        ]

        # --- Calculate Both LRCs ---
        # The projected LRC is calculated up to the inflection point and drawn from there.
        lrc_projected_params = calculate_lrc_parameters_for_api(candles, use_date, start_ts, inflection_ts)

        # The full-range LRC is calculated on all data from the start date.
        # We'll reuse the same calculation function but without an inflection point.
        lrc_full_params = calculate_lrc_parameters_for_api(candles, use_date, start_ts, None)

        return jsonify({
            'candles': candles,
            'lrc': { # Primary (projected) channel
                'params': lrc_projected_params,
                'deviations': deviations
            },
            'lrc_full': { # Secondary (full-range) channel
                'params': lrc_full_params,
                'deviations': deviations
            }
        })

    except Exception as e:
        print(f"Error in /api/lrc-data: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001) 