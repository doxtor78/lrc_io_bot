import ccxt
import time
import pandas as pd
import numpy as np
from datetime import datetime
import json

from config import BITMEX_TESTNET_API_KEY, BITMEX_TESTNET_API_SECRET

# --- Configuration ---
SYMBOL = 'XBTUSD'  # Using XBTUSD for BitMEX Testnet
TIMEFRAME = '1h'
DEVIATION = 1.0    # Number of standard deviations for the channel
ORDER_SIZE = 100   # Number of contracts to trade
POLL_INTERVAL_S = 60 # Check every 60 seconds

# --- LRC Calculation Logic (adapted from backtester) ---
def calculate_lrc_parameters(data):
    if len(data) < 2:
        return {}
    
    source_prices = np.array([d['close'] for d in data])
    indices = np.arange(len(source_prices))
    slope, intercept = np.polyfit(indices, source_prices, 1)
    
    regression_values = slope * indices + intercept
    deviations = source_prices - regression_values
    std_dev = np.std(deviations)
    
    return {'slope': slope, 'intercept': intercept, 'std_dev': std_dev}

# --- Exchange Interaction ---
def initialize_exchange():
    """Initializes and returns the CCXT exchange instance for BitMEX Testnet."""
    exchange = ccxt.bitmex({
        'apiKey': BITMEX_TESTNET_API_KEY,
        'secret': BITMEX_TESTNET_API_SECRET,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True) # IMPORTANT for Testnet
    return exchange

def get_current_position(exchange, symbol):
    """
    Fetches the current position size.
    This version fetches all positions and filters to find the correct one,
    making it more robust, especially on restarts.
    """
    try:
        # Fetch all positions from the account
        all_positions = exchange.fetch_positions()
        
        # Find the specific position for our symbol
        for position in all_positions:
            if position.get('info', {}).get('symbol') == symbol:
                # 'contracts' is the standard field for position size in ccxt
                return position.get('contracts', 0)
        
        # If the loop completes without finding our symbol, we have no position.
        return 0
        
    except Exception as e:
        print(f"Error fetching position: {e}")
        return 0

# --- Main Bot Logic ---
def run_bot():
    print("--- Starting Live LRC I/O Bot on BitMEX Testnet ---")
    exchange = initialize_exchange()
    
    print(f"Bot configured for {SYMBOL} on {TIMEFRAME} timeframe.")
    print(f"Trading with {DEVIATION} std deviations and order size of {ORDER_SIZE} contracts.")

    while True:
        try:
            print(f"\n[{datetime.now().isoformat()}] --- New Cycle ---")
            
            # 1. Fetch data
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100) # Fetch 100 candles
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            data_for_lrc = [{'close': row['close'], 'time': int(row['timestamp'].timestamp())} for index, row in df.iterrows()]
            
            # 2. Calculate LRC
            lrc_params = calculate_lrc_parameters(data_for_lrc)
            if not lrc_params:
                print("Could not calculate LRC params. Waiting for next cycle.")
                time.sleep(POLL_INTERVAL_S)
                continue
                
            slope = lrc_params['slope']
            intercept = lrc_params['intercept']
            std_dev = lrc_params['std_dev']

            # 3. Calculate current channel values for the latest candle
            latest_index = len(df) - 1
            mid_line = slope * latest_index + intercept
            upper_band = mid_line + DEVIATION * std_dev
            lower_band = mid_line - DEVIATION * std_dev
            
            latest_price = df['close'].iloc[-1]
            print(f"Latest Price: {latest_price:.2f} | Lower: {lower_band:.2f} | Upper: {upper_band:.2f}")

            # 4. Check position and execute trades
            current_position_size = get_current_position(exchange, SYMBOL)
            print(f"Current Position Size: {current_position_size} contracts")

            # --- Trading Strategy ---
            # If we have no position, look for an entry.
            if current_position_size == 0:
                if latest_price < lower_band:
                    print(f"*** SIGNAL: Price {latest_price} is below lower band {lower_band}. Placing LONG order. ***")
                    
                    # --- SAFETY CHECK ---
                    # Programmatically enforce that we only buy when our position is zero.
                    # If this fails, the bot will stop, preventing unwanted positions.
                    assert current_position_size == 0, f"SAFETY CHECK FAILED: Bot attempted to buy with an existing position of {current_position_size} contracts."

                    order = exchange.create_market_buy_order(SYMBOL, ORDER_SIZE)
                    print("Buy order placed:", json.dumps(order, indent=2))
                else:
                    print("No entry signal. Price is not below lower band.")
            
            # If we are in a position, look for an exit.
            elif current_position_size > 0: # Assumes we are LONG
                if latest_price > upper_band:
                    print(f"*** SIGNAL: Price {latest_price} is above upper band {upper_band}. Closing LONG position. ***")
                    order = exchange.create_market_sell_order(SYMBOL, current_position_size, {'reduceOnly': True})
                    print("Sell order (close) placed:", json.dumps(order, indent=2))
                else:
                    print("No exit signal. Holding position.")
            
        except ccxt.NetworkError as e:
            print(f"Network Error: {e}. Retrying in {POLL_INTERVAL_S}s...")
        except ccxt.ExchangeError as e:
            print(f"Exchange Error: {e}. Retrying in {POLL_INTERVAL_S}s...")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        time.sleep(POLL_INTERVAL_S)

if __name__ == '__main__':
    run_bot() 