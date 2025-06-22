import ccxt
import json
import time
import os
from datetime import datetime
import numpy as np

# --- Constants ---
SYMBOL = 'BTC/USDT'
# TIMEFRAME will be loaded from params file
PARAMS_FILE = 'stable_v3/lrc_params.json'
POLL_INTERVAL_S = 60 # Check for signals every 60 seconds

# --- Exchange Credentials (from app.py) ---
# For your security, please REVOKE these keys from your Binance account after this session.
# In real applications, use environment variables.
BINANCE_API_KEY = "8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7"
BINANCE_SECRET_KEY = "jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO"

def load_lrc_params():
    """Loads LRC parameters from the JSON file."""
    try:
        with open(PARAMS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: LRC parameters file not found at {PARAMS_FILE}.")
        return None
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {PARAMS_FILE}.")
        return None

def initialize_exchange():
    """Initializes and returns the CCXT exchange instance."""
    exchange = ccxt.binance({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_SECRET_KEY,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future', # Or 'spot'
        }
    })
    return exchange

def check_for_signal(exchange, lrc_data):
    """
    Checks for a trading signal based on the latest candle and LRC data.
    """
    if not lrc_data or 'params' not in lrc_data:
        print("LRC data is missing or invalid. Skipping signal check.")
        return

    timeframe = lrc_data.get('timeframe', '1h') # Default to 1h if not found
    lrc_params = lrc_data['params']
    std_dev = lrc_params.get('std_dev')
    slope = lrc_params.get('slope')
    intercept = lrc_params.get('intercept')
    lrc_start_time = lrc_params.get('start_time')

    if not all([std_dev, slope is not None, intercept is not None, lrc_start_time]):
        print("Required LRC parameters (std_dev, slope, intercept, start_time) not found. Skipping.")
        return

    print("Fetching latest candle...")
    try:
        timeframe_seconds = exchange.parse_timeframe(timeframe)
        latest_candle = exchange.fetch_ohlcv(SYMBOL, timeframe, limit=1)[0]
        # [timestamp, open, high, low, close, volume]
        latest_candle_ts = latest_candle[0] / 1000 # ms to s
        close_price = latest_candle[4]

        # Calculate the bar index relative to the LRC start time
        current_bar_index = (latest_candle_ts - lrc_start_time) / timeframe_seconds
        
        # Project the midline to the current bar
        mid_line_price = slope * current_bar_index + intercept
        
        upper_1_sigma = mid_line_price + std_dev
        lower_1_sigma = mid_line_price - std_dev

        print(f"[{datetime.now().isoformat()}] Current Close: {close_price:.2f} | Projected Midline: {mid_line_price:.2f} | Upper 1σ: {upper_1_sigma:.2f} | Lower 1σ: {lower_1_sigma:.2f}")

        # According to pseudocode, slope direction determines trade preference.
        if close_price > upper_1_sigma:
            print("!!! SIGNAL: Price is above +1σ. Checking for SHORT signal. !!!")
            if slope < 0:
                handle_entry_signal('SHORT', exchange, mid_line_price, std_dev, close_price)
            else:
                print("Signal ignored: slope is not favorable for a SHORT position.")
        elif close_price < lower_1_sigma:
            print("!!! SIGNAL: Price is below -1σ. Checking for LONG signal. !!!")
            if slope > 0:
                handle_entry_signal('LONG', exchange, mid_line_price, std_dev, close_price)
            else:
                print("Signal ignored: slope is not favorable for a LONG position.")
        else:
            print("No signal detected. Price is within +/-1σ.")

    except ccxt.NetworkError as e:
        print(f"Network error while fetching candle: {e}")
    except Exception as e:
        print(f"An error occurred during signal check: {e}")

def handle_entry_signal(side, exchange, mid_line_price, std_dev, current_price):
    """Handles the logic for placing entry and stop-loss orders."""
    print(f"--- Handling {side} Entry Signal ---")
    
    # Determine price levels based on signal side
    # For a LONG signal, we buy between -1σ and -3σ. SL is at -4σ.
    # For a SHORT signal, we sell between +1σ and +3σ. SL is at +4σ.
    
    direction = 1 if side == 'SHORT' else -1
    
    entry_zone_start = mid_line_price + (direction * std_dev * 1)
    entry_zone_end = mid_line_price + (direction * std_dev * 3)
    stop_loss_price = mid_line_price + (direction * std_dev * 4)
    
    # Create 5 evenly distributed entry points in the zone
    entry_prices = np.linspace(entry_zone_start, entry_zone_end, 5)
    
    print(f"Side: {side}")
    print(f"Entry zone: {entry_zone_start:.2f} to {entry_zone_end:.2f}")
    print(f"Calculated Entry Prices: {[f'{p:.2f}' for p in entry_prices]}")
    print(f"Stop Loss Price: {stop_loss_price:.2f}")
    
    # TODO - Order Placement Logic:
    # 1. Check for existing positions/orders to avoid duplicates.
    # 2. Determine order size (e.g., 1% of portfolio per sub-order).
    # 3. Place 5 limit orders for entry.
    #    - For LONG, these are 'buy' limit orders.
    #    - For SHORT, these are 'sell' limit orders.
    # 4. Place 1 stop-market or stop-limit order for the combined position.

def main():
    """Main bot loop."""
    print("--- LRC Trading Bot Starting ---")
    exchange = initialize_exchange()
    
    print(f"Bot configured for {SYMBOL}.")
    print(f"Polling for signals every {POLL_INTERVAL_S} seconds.")
    
    while True:
        print("\n" + "="*40)
        lrc_data = load_lrc_params()
        
        if lrc_data:
            check_for_signal(exchange, lrc_data)
        else:
            print("Waiting for LRC parameters to be generated from the web UI...")

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main() 