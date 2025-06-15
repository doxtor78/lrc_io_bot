import ccxt
import json
import os
import time
import logging
from dotenv import load_dotenv

# --- Setup ---
# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Functions ---
def load_config():
    """Loads the configuration from config.json."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found. Please create it.")
        return None
    except json.JSONDecodeError:
        logger.error("Error decoding config.json. Please check its format.")
        return None

def initialize_exchange():
    """Initializes and returns the CCXT exchange object."""
    api_key = os.getenv('BITMEX_TESTNET_API_KEY')
    api_secret = os.getenv('BITMEX_TESTNET_API_SECRET')

    if not api_key or not api_secret:
        logger.error("API keys not found in .env file. Please add them.")
        return None

    exchange = ccxt.bitmex({
        'apiKey': api_key,
        'secret': api_secret,
    })
    # Use the testnet
    exchange.set_sandbox_mode(True)
    return exchange

# --- Main Application Logic ---
def main():
    logger.info("Starting live trading bot...")

    config = load_config()
    if not config:
        return

    exchange = initialize_exchange()
    if not exchange:
        return

    symbol = config['symbol']
    timeframe = config['timeframe']
    
    logger.info(f"Configuration loaded: Trading {symbol} on {timeframe} timeframe.")

    try:
        # Main loop
        while True:
            logger.info("Checking for new data and trading signals...")
            
            # --- In the next steps, we will add the logic here to: ---
            # 1. Fetch the latest OHLCV data.
            # 2. Calculate the SMA.
            # 3. Determine the strategy signal (IN or OUT).
            # 4. Manage the bot's state (Are we in a position? Do we want to exit?).
            # 5. Place, check, and cancel orders via the exchange API.
            
            # Wait for the next candle
            # (e.g., for '1h' timeframe, we would sleep for an hour, 
            # but for development we'll use a shorter interval)
            sleep_duration = 60 # seconds
            logger.info(f"Sleeping for {sleep_duration} seconds...")
            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main() 