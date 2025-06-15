from pybit.unified_trading import HTTP
import time
import logging
from config import *

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BybitTestnetBot:
    def __init__(self):
        self.session = HTTP(
            testnet=True,
            api_key=API_KEY,
            api_secret=API_SECRET
        )
        self.setup_account()

    def setup_account(self):
        """Set up account parameters like leverage"""
        try:
            # Set leverage
            self.session.set_leverage(
                category="linear",
                symbol=SYMBOL,
                buyLeverage=str(LEVERAGE),
                sellLeverage=str(LEVERAGE)
            )
            logger.info(f"Set leverage to {LEVERAGE}x for {SYMBOL}")
        except Exception as e:
            logger.error(f"Error setting up account: {e}")

    def get_account_balance(self):
        """Get account balance"""
        try:
            response = self.session.get_wallet_balance(
                accountType="UNIFIED",
                coin="USDT"
            )
            return response['result']['list'][0]['totalWalletBalance']
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None

    def place_market_order(self, side, quantity):
        """Place a market order"""
        try:
            response = self.session.place_order(
                category="linear",
                symbol=SYMBOL,
                side=side,
                orderType="Market",
                qty=str(quantity)
            )
            logger.info(f"Placed {side} order: {response}")
            return response
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def get_position(self):
        """Get current position"""
        try:
            response = self.session.get_positions(
                category="linear",
                symbol=SYMBOL
            )
            return response['result']['list'][0]
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None

def main():
    bot = BybitTestnetBot()
    
    # Example: Get account balance
    balance = bot.get_account_balance()
    logger.info(f"Account balance: {balance} USDT")

    # Example: Get current position
    position = bot.get_position()
    logger.info(f"Current position: {position}")

if __name__ == "__main__":
    main() 