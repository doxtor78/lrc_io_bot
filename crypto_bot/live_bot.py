import ccxt
import json
import os
import time
import logging
import pandas as pd
from dotenv import load_dotenv

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

# --- Functions ---
def load_config():
    """Loads the configuration from config.json."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found.")
        return None

def initialize_exchange():
    """Initializes and returns the CCXT exchange object."""
    api_key = os.getenv('BITMEX_TESTNET_API_KEY')
    api_secret = os.getenv('BITMEX_TESTNET_API_SECRET')
    if not api_key or "YOUR_API_KEY" in api_key or not api_secret or "YOUR_API_SECRET" in api_secret:
        logger.error("API keys not found or are placeholders in .env file.")
        return None
    logger.info("Initializing connection to BitMEX testnet...")
    exchange = ccxt.bitmex({'apiKey': api_key, 'secret': api_secret})
    exchange.set_sandbox_mode(True)
    return exchange

def load_state():
    """Loads the bot's state from state.json."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'status': 'OUT'} # Default state

def save_state(state):
    """Saves the bot's state to state.json."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# --- Main Application Logic ---
def main():
    logger.info("--- Starting live trading bot ---")
    config = load_config()
    if not config: return
    
    exchange = initialize_exchange()
    if not exchange: return

    state = load_state()
    logger.info(f"Loaded initial state: {state}")

    symbol = config['symbol']
    timeframe = config['timeframe']
    sma_window = config['sma_window']
    order_size_contracts = config.get('order_size_contracts', 100)
    
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
            
            logger.info(f"Current Price: {price:.2f}, SMA({sma_window}): {sma:.2f}.")

            # 3. Get current position from exchange
            try:
                # For BitMEX perpetual swaps, we check the 'contracts' in our balance
                balance = exchange.fetch_balance()
                # Find the correct asset in the balance info. For XBTUSD it is 'XBT'
                position_size_contracts = 0
                for asset in balance['info']:
                    if asset['asset'] == 'XBT':
                        position_size_contracts = asset.get('currentQty', 0)
                        break
                logger.info(f"Current Position: {position_size_contracts} contracts.")
            except Exception as e:
                logger.error(f"Could not fetch position: {e}")
                time.sleep(60)
                continue

            # --- TRADING LOGIC ---
            # Determine desired position: +order_size_contracts for long, -order_size_contracts for short
            desired_position = 0
            if price > sma:
                desired_position = order_size_contracts
                logger.info("Signal: LONG (price > MA)")
            elif price < sma:
                desired_position = -order_size_contracts
                logger.info("Signal: SHORT (price < MA)")
            else:
                logger.info("Signal: FLAT (price == MA)")

            # Place limit order if position needs to change
            if position_size_contracts != desired_position:
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    if desired_position > position_size_contracts:
                        # Need to buy (open/increase long or close short)
                        amount = abs(desired_position - position_size_contracts)
                        price_to_use = ticker['ask']
                        logger.info(f"Placing LIMIT BUY for {amount} contracts at {price_to_use}")
                        exchange.create_limit_buy_order(symbol, amount, price_to_use)
                    elif desired_position < position_size_contracts:
                        # Need to sell (open/increase short or close long)
                        amount = abs(desired_position - position_size_contracts)
                        price_to_use = ticker['bid']
                        logger.info(f"Placing LIMIT SELL for {amount} contracts at {price_to_use}")
                        exchange.create_limit_sell_order(symbol, amount, price_to_use)
                except Exception as e:
                    logger.error(f"Order placement failed: {e}")
            else:
                logger.info("No position change needed.")

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