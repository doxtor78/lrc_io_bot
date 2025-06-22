import ccxt
import os
import json
import logging
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
logger = logging.getLogger("PositionCloser")
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

# --- Main Logic ---
def main():
    logger.info("--- Starting Position Closer Script ---")

    config = load_config()
    if not config:
        return

    exchange = initialize_exchange()
    if not exchange:
        return

    symbol = config['symbol']
    
    try:
        # Fetch current position using the reliable private API method
        logger.info(f"Fetching position for {symbol}...")
        all_positions_raw = exchange.private_get_position()
        
        position_size_contracts = 0
        for p in all_positions_raw:
            if p.get('symbol') == symbol:
                position_size_contracts = int(p.get('currentQty') or 0)
                break

        if position_size_contracts > 0:
            logger.info(f"Found LONG position of {position_size_contracts} contracts. Closing it now.")
            try:
                # To close a long position, we sell the exact amount fetched.
                order = exchange.create_market_sell_order(symbol, position_size_contracts, {'execInst': 'Close'})
                logger.info(f"Market SELL order to close position placed: {order}")
                logger.info("Position closed successfully.")
            except Exception as e:
                logger.error(f"Failed to place closing SELL order: {e}")
        elif position_size_contracts < 0:
            logger.info(f"Found SHORT position of {position_size_contracts} contracts. Closing it now.")
            try:
                # To close a short position, we buy the exact amount fetched.
                order = exchange.create_market_buy_order(symbol, abs(position_size_contracts), {'execInst': 'Close'})
                logger.info(f"Market BUY order to close position placed: {order}")
                logger.info("Position closed successfully.")
            except Exception as e:
                logger.error(f"Failed to place closing BUY order: {e}")
        else:
            logger.info("No open position found for this symbol.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main() 