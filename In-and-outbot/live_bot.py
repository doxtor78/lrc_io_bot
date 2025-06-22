import ccxt
import json
import os
import time
import logging
import pandas as pd
from dotenv import load_dotenv
import requests
from datetime import datetime, timezone

# --- Setup ---
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
STATE_FILE = "state.json"

# --- Time Synchronization ---
def get_server_time():
    """Get BitMEX server time for synchronization"""
    try:
        response = requests.get('https://testnet.bitmex.com/api/v1/announcement')
        server_time = response.headers.get('Date')
        if server_time:
            server_timestamp = pd.to_datetime(server_time).timestamp()
            local_timestamp = time.time()
            time_offset = server_timestamp - local_timestamp
            logger.info(f"Time offset from server: {time_offset:.2f} seconds")
            return time_offset
    except Exception as e:
        logger.warning(f"Could not get server time: {e}")
    return 0

def resync_time(exchange):
    """Periodically resync time with the server."""
    logger.info("Resynchronizing time with server...")
    time_offset = get_server_time()
    # get_server_time returns 0 on failure, so we can't check for None.
    # We will update it anyway. A zero offset is better than a stale one if sync fails.
    exchange.options['timeDifference'] = time_offset * 1000
    logger.info(f"Time offset updated to: {time_offset:.2f} seconds")

# --- Config ---
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found.")
        return None

def initialize_exchange():
    api_key = os.getenv('BITMEX_TESTNET_API_KEY')
    api_secret = os.getenv('BITMEX_TESTNET_API_SECRET')
    if not api_key or "YOUR_API_KEY" in api_key or not api_secret or "YOUR_API_SECRET" in api_secret:
        logger.error("API keys not found or are placeholders in .env file.")
        return None
    logger.info("Initializing connection to BitMEX testnet...")
    
    # Get time offset for synchronization
    time_offset = get_server_time()
    
    exchange = ccxt.bitmex({
        'apiKey': api_key, 
        'secret': api_secret,
        'timeout': 30000,  # 30 seconds timeout
        'rateLimit': 1000,  # 1 second between requests
        'enableRateLimit': True,
        'options': {
            'adjustForTimeDifference': True,
            'timeDifference': time_offset * 1000,  # Convert to milliseconds
        }
    })
    exchange.set_sandbox_mode(True)
    
    # Test connection
    try:
        exchange.load_markets()
        logger.info("Successfully connected to BitMEX testnet")
        return exchange
    except Exception as e:
        logger.error(f"Failed to connect to BitMEX: {e}")
        return None

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        'last_signal': None,
        'open_order_id': None,
        'open_order_side': None,
        'open_order_price': None,
        'position_size': 0,
        'signal_confirm_count': 0
    }

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# --- Utility Functions ---
def round_to_tick(price, tick_size):
    return round(round(price / tick_size) * tick_size, 8)

# --- Exchange Functions ---
def fetch_position(exchange, symbol):
    try:
        logger.info("Fetching position...")
        # Add retry logic for API calls
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to fetch position (attempt {attempt + 1}/{max_retries})")
                positions = exchange.private_get_position()
                logger.info("Successfully fetched position data.")
                for pos in positions:
                    if pos.get('symbol') == symbol:
                        position_size = int(pos.get('currentQty', 0))
                        logger.info(f"Position for {symbol}: {position_size}")
                        return position_size
                logger.info(f"No position found for {symbol}.")
                return 0
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying position fetch (attempt {attempt + 1}): {e}")
                    time.sleep(2)
                else:
                    raise e
    except Exception as e:
        logger.error(f"Could not fetch position: {e}")
        return None

def fetch_open_orders(exchange, symbol):
    try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return exchange.fetch_open_orders(symbol)
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying open orders fetch (attempt {attempt + 1}): {e}")
                    time.sleep(2)
                else:
                    raise e
    except Exception as e:
        logger.error(f"Could not fetch open orders: {e}")
        return []

def cancel_all_orders(exchange, symbol):
    try:
        open_orders = fetch_open_orders(exchange, symbol)
        for order in open_orders:
            exchange.cancel_order(order['id'], symbol)
            logger.info(f"Cancelled order {order['id']}")
    except Exception as e:
        logger.error(f"Error cancelling orders: {e}")

# --- Signal Logic ---
def get_signal(df, sma_window):
    price = df['close'].iloc[-1]
    sma = df['close'].rolling(window=sma_window).mean().iloc[-1]
    if price > sma:
        return 'long', price, sma
    elif price < sma:
        return 'short', price, sma
    else:
        return 'flat', price, sma

# --- Order Management ---
def place_limit_order(exchange, symbol, side, amount, price, tick_size):
    price = round_to_tick(price, tick_size)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if side == 'buy':
                order = exchange.create_limit_buy_order(symbol, amount, price)
            else:
                order = exchange.create_limit_sell_order(symbol, amount, price)
            
            fee_info = order.get('fee', {})
            fee_cost = fee_info.get('cost', 'N/A')
            fee_currency = fee_info.get('currency', '')
            
            logger.info(f"Placed {side.upper()} LIMIT order for {amount} at {price}. Fee: {fee_cost} {fee_currency}")
            
            return order
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Retrying order placement (attempt {attempt + 1}): {e}")
                time.sleep(2)
            else:
                logger.error(f"Failed to place {side} order: {e}")
                return None

def amend_order(exchange, symbol, order_id, new_price, tick_size):
    new_price = round_to_tick(new_price, tick_size)
    try:
        order = exchange.fetch_order(order_id, symbol)
        if order['status'] in ['open', 'partially_filled']:
            exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order {order_id} to amend price.")
            side = order['side']
            amount = order['remaining']
            new_order = place_limit_order(exchange, symbol, side, amount, new_price, tick_size)
            if new_order:
                logger.info(f"Amended order {order_id} to new price {new_price}, new order {new_order['id']}")
                return new_order['id']
            return None
        else:
            logger.info(f"Order {order_id} already filled or closed.")
            return None
    except Exception as e:
        logger.error(f"Failed to amend order: {e}")
        return None

def close_position(exchange, symbol, position_size, tick_size):
    try:
        ticker = exchange.fetch_ticker(symbol)
        action_time = time.time()
        if position_size > 0:
            # Close long
            price = ticker['bid']
            print(f"[ACTION] Closing LONG position with SELL LIMIT order for {abs(position_size)} at {price}")
            logger.info(f"Closing LONG position with SELL order at {price}")
            order = place_limit_order(exchange, symbol, 'sell', abs(position_size), price, tick_size)
            if order:
                elapsed = time.time() - action_time
                print(f"[TIMING] Time to CLOSE LONG after signal: {elapsed:.2f} seconds")
                logger.info(f"Time to CLOSE LONG after signal: {elapsed:.2f} seconds")
                logger.info(f"Closing LONG position with SELL order {order['id']}")
                return order['id']
            return None
        elif position_size < 0:
            # Close short
            price = ticker['ask']
            print(f"[ACTION] Closing SHORT position with BUY LIMIT order for {abs(position_size)} at {price}")
            logger.info(f"Closing SHORT position with BUY order at {price}")
            order = place_limit_order(exchange, symbol, 'buy', abs(position_size), price, tick_size)
            if order:
                elapsed = time.time() - action_time
                print(f"[TIMING] Time to CLOSE SHORT after signal: {elapsed:.2f} seconds")
                logger.info(f"Time to CLOSE SHORT after signal: {elapsed:.2f} seconds")
                logger.info(f"Closing SHORT position with BUY order {order['id']}")
                return order['id']
            return None
        else:
            logger.info("No position to close.")
            return None
    except Exception as e:
        logger.error(f"Failed to close position: {e}")
        return None

def open_position(exchange, symbol, side, amount, tick_size):
    try:
        ticker = exchange.fetch_ticker(symbol)
        action_time = time.time()
        price = ticker['ask'] if side == 'buy' else ticker['bid']
        print(f"[ACTION] Opening {side.upper()} position with LIMIT order for {amount} at {price}")
        logger.info(f"Opening {side.upper()} position with order at {price}")
        order = place_limit_order(exchange, symbol, side, amount, price, tick_size)
        if order:
            elapsed = time.time() - action_time
            print(f"[TIMING] Time to OPEN {side.upper()} after signal: {elapsed:.2f} seconds")
            logger.info(f"Time to OPEN {side.upper()} after signal: {elapsed:.2f} seconds")
            logger.info(f"Opening {side.upper()} position with order {order['id']}")
            return order['id']
        return None
    except Exception as e:
        logger.error(f"Failed to open position: {e}")
        return None

# --- Main Application Logic ---
def main():
    logger.info("--- Starting robust in-and-out trading bot ---")
    config = load_config()
    if not config: return
    
    # Initialize exchange with better error handling
    exchange = initialize_exchange()
    if not exchange: return
    
    state = load_state()
    logger.info(f"Loaded initial state: {state}")

    symbol = config['symbol']
    timeframe = config['timeframe']
    sma_window = config['sma_window']
    order_size_contracts = config.get('order_size_contracts', 100)
    tick_size = config.get('tick_size', 0.5)
    signal_confirm_bars = config.get('signal_confirm_bars', 1)
    order_timeout = config.get('order_timeout', 30)  # seconds

    logger.info(f"Configuration: Trading {symbol} on {timeframe} with SMA window {sma_window}.")
    logger.info(f"Order size: {order_size_contracts} contracts. Tick size: {tick_size}")

    # Connection health check counter
    connection_errors = 0
    max_connection_errors = 5
    last_resync_time = time.time()

    try:
        while True:
            logger.info("--- New Cycle ---")
            
            # Resync time every 30 minutes to avoid clock drift issues
            if time.time() - last_resync_time > 1800:
                resync_time(exchange)
                last_resync_time = time.time()
            
            # 1. Fetch market data with retry logic
            try:
                max_retries = 3
                ohlcv = None
                for attempt in range(max_retries):
                    try:
                        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=sma_window + 5)
                        connection_errors = 0  # Reset error counter on success
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Retrying market data fetch (attempt {attempt + 1}): {e}")
                            time.sleep(5)
                        else:
                            raise e
                
                if ohlcv is None:
                    raise Exception("Failed to fetch market data after retries")
                    
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
            except Exception as e:
                logger.error(f"Could not fetch market data: {e}")
                connection_errors += 1
                if connection_errors >= max_connection_errors:
                    logger.error("Too many connection errors. Reinitializing exchange...")
                    exchange = initialize_exchange()
                    if not exchange:
                        logger.error("Failed to reinitialize exchange. Exiting.")
                        return
                    connection_errors = 0
                time.sleep(60)
                continue

            # 2. Calculate signal
            signal, price, sma = get_signal(df, sma_window)
            logger.info(f"Current Price: {price:.2f}, SMA({sma_window}): {sma:.2f}. Signal: {signal}")

            # 3. Signal confirmation logic
            if signal == state.get('last_signal'):
                state['signal_confirm_count'] += 1
            else:
                state['signal_confirm_count'] = 1
                state['last_signal'] = signal
            save_state(state)
            if state['signal_confirm_count'] < signal_confirm_bars:
                logger.info(f"Waiting for signal confirmation: {state['signal_confirm_count']}/{signal_confirm_bars}")
                time.sleep(60)
                continue

            # 4. Fetch position
            logger.info("Checking current position...")
            position_size = fetch_position(exchange, symbol)
            if position_size is None:
                time.sleep(60)
                continue
            state['position_size'] = position_size
            save_state(state)

            # 5. Order management
            open_orders = fetch_open_orders(exchange, symbol)
            if open_orders:
                logger.info(f"Found {len(open_orders)} open order(s). Managing...")
                for order in open_orders:
                    try:
                        # If order is too far from market, amend
                        ticker = exchange.fetch_ticker(symbol)
                        best_price = ticker['ask'] if order['side'] == 'buy' else ticker['bid']
                        price_diff = abs(order['price'] - best_price)
                        if price_diff > tick_size:
                            logger.info(f"Amending order {order['id']} from {order['price']} to {best_price}")
                            amend_order(exchange, symbol, order['id'], best_price, tick_size)
                        # If order is too old, cancel and replace
                        order_age = (pd.Timestamp.now() - pd.to_datetime(order['timestamp'], unit='ms')).total_seconds()
                        if order_age > order_timeout:
                            logger.info(f"Order {order['id']} is too old ({order_age:.2f}s), cancelling.")
                            exchange.cancel_order(order['id'], symbol)
                    except Exception as e:
                        logger.error(f"Error managing order {order.get('id', 'unknown')}: {e}")
                time.sleep(10)
                continue  # Wait for next cycle after managing orders

            # 6. Main strategy logic (in-and-out)
            action_taken = False
            if signal == 'long' and position_size <= 0:
                if position_size < 0:
                    logger.info("Reversing from SHORT to LONG.")
                    close_position(exchange, symbol, position_size, tick_size)
                    time.sleep(2)
                open_position(exchange, symbol, 'buy', order_size_contracts, tick_size)
                action_taken = True
            elif signal == 'short' and position_size >= 0:
                if position_size > 0:
                    logger.info("Reversing from LONG to SHORT.")
                    close_position(exchange, symbol, position_size, tick_size)
                    time.sleep(2)
                open_position(exchange, symbol, 'sell', order_size_contracts, tick_size)
                action_taken = True
            elif signal == 'flat' and position_size != 0:
                logger.info("Signal is FLAT, closing position.")
                close_position(exchange, symbol, position_size, tick_size)
                action_taken = True
            else:
                logger.info("No action needed. Signal and position are aligned.")

            if action_taken:
                time.sleep(5)
            else:
                time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Bot stopped manually. Cancelling all open orders...")
        cancel_all_orders(exchange, symbol)
        save_state(state)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        cancel_all_orders(exchange, symbol)
        save_state(state)

if __name__ == "__main__":
    main()