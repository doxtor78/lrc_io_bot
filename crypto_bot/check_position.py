import ccxt
import os
import json
import logging
from dotenv import load_dotenv

# --- Setup ---
load_dotenv()
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("PositionChecker")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# --- Functions ---
def load_config():
    """Loads the configuration from config.json."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{CONFIG_FILE} not found.")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding {CONFIG_FILE}.")
        return None

def initialize_exchange():
    """Initializes and returns the CCXT exchange object."""
    api_key = os.getenv('BITMEX_TESTNET_API_KEY')
    api_secret = os.getenv('BITMEX_TESTNET_API_SECRET')

    if not api_key or not api_secret:
        logger.error("API keys not found in .env file.")
        return None

    exchange = ccxt.bitmex({
        'apiKey': api_key,
        'secret': api_secret,
    })
    exchange.set_sandbox_mode(True)
    return exchange

# --- Main Logic ---
def main():
    logger.info("--- Checking Current Position ---")

    config = load_config()
    if not config:
        return

    exchange = initialize_exchange()
    if not exchange:
        return

    symbol = config['symbol']
    
    try:
        logger.info(f"Fetching position for {symbol}...")
        
        # Use the reliable private API method to get position data
        all_positions_raw = exchange.private_get_position()
        position_size_contracts = 0
        position_found = False
        for p in all_positions_raw:
            if p.get('symbol') == symbol and p.get('isOpen', False):
                position_size_contracts = p.get('currentQty', 0)
                position_found = True
                break
        
        if position_found:
            logger.info(f"✅ Open Position Found: {position_size_contracts} contracts for {symbol}.")
        else:
            logger.info(f"✅ No open position found for {symbol}.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main() 