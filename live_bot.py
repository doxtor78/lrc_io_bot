import ccxt
import json
import os
import time
import logging
import pandas as pd
from dotenv import load_dotenv

# --- Setup ---
# Load environment variables from .env file
load_dotenv()

# Get the absolute path of the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, "bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
STATE_FILE = os.path.join(SCRIPT_DIR, "state.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# --- Functions ---
def load_config():
    """Loads the configuration from config.json."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{CONFIG_FILE} not found. Please create it.")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding {CONFIG_FILE}. Please check its format.")
        return None

def initialize_exchange():
    """Initializes and returns the CCXT exchange object."""
    api_key = os.getenv('BITMEX_TESTNET_API_KEY')
    api_secret = os.getenv('BITMEX_TESTNET_API_SECRET')

    if not api_key or not api_secret:
        logger.error("API keys not found in .env file. Please add them.")
        return None

    logger.info("Initializing connection to BitMEX testnet...")
    exchange = ccxt.bitmex({
        'apiKey': api_key,
        'secret': api_secret,
    })
    # Use the testnet
    exchange.set_sandbox_mode(True)
    return exchange

def load_state():
    """Loads the bot's state from state.json."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'status': 'OUT', 'open_order_id': None} # Default state

def save_state(state):
    """Saves the bot's state to state.json."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# --- Main Application Logic ---
def main():
    logger.info("--- Starting live trading bot ---")

    config = load_config()
    if not config:
        return

    exchange = initialize_exchange()
    if not exchange:
        return

    state = load_state()
    logger.info(f"Loaded initial state: {state}")

    symbol = config['symbol']
    timeframe = config['timeframe']
    sma_window = config['sma_window']
    order_size_contracts = config['order_size_contracts']
    
    logger.info(f"Configuration: Trading {symbol} on {timeframe} with SMA window {sma_window}.")
    logger.info(f"Order size: {order_size_contracts} contracts.")

    try:
        while True:
            logger.info("--- New Cycle ---")
            
            # 1. Fetch market data
            logger.info(f"Fetching {sma_window + 5} candles for {symbol}...")
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=sma_window + 5)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                logger.info(f"Successfully fetched {len(df)} candles. Last close: {df.iloc[-1]['close']}")
            except Exception as e:
                logger.error(f"Could not fetch market data: {e}")
                time.sleep(60)
                continue

            # 2. Calculate strategy signal
            df['sma'] = df['close'].rolling(window=sma_window).mean()
            price = df['close'].iloc[-1]
            sma = df['sma'].iloc[-1]
            
            # Determine signal: 1 for 'IN', 0 for 'OUT'
            strategy_signal = 1 if price > sma else 0
            
            logger.info(f"Current Price: {price:.2f}, SMA({sma_window}): {sma:.2f}. Strategy Signal: {'IN' if strategy_signal == 1 else 'OUT'}")

            # 3. Get current position from exchange
            try:
                # For BitMEX perpetual swaps, we check the 'contracts' in our balance
                balance = exchange.fetch_balance()
                position_size_contracts = balance['info'][0].get('currentQty', 0)
                logger.info(f"Current Position: {position_size_contracts} contracts.")
            except Exception as e:
                logger.error(f"Could not fetch position: {e}")
                time.sleep(60)
                continue

            # --- Trading Logic ---
            # Decision making based on strategy signal and current position
            
            # Case 1: Strategy signals 'IN', but we are 'OUT' (no position)
            if strategy_signal == 1 and position_size_contracts == 0:
                logger.info("Signal is IN and no position is open. Placing MARKET BUY order.")
                try:
                    order = exchange.create_market_buy_order(symbol, order_size_contracts)
                    logger.info(f"Market BUY order placed: {order}")
                    # No need to update state here for simple market orders, 
                    # as position will be updated in the next cycle.
                except Exception as e:
                    logger.error(f"Failed to place BUY order: {e}")

            # Case 2: Strategy signals 'OUT', but we are 'IN' (have a position)
            elif strategy_signal == 0 and position_size_contracts != 0:
                logger.info("Signal is OUT and a position is open. Placing MARKET SELL to close.")
                try:
                    # To close a long position, we sell the same amount.
                    order = exchange.create_market_sell_order(symbol, abs(position_size_contracts))
                    logger.info(f"Market SELL order (close) placed: {order}")
                except Exception as e:
                    logger.error(f"Failed to place SELL order: {e}")
            
            # Case 3: No action needed
            else:
                logger.info("No action needed. Signal and position are aligned.")
            
            # Wait for the next cycle
            sleep_duration = 60
            logger.info(f"Sleeping for {sleep_duration} seconds...")
            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main() 