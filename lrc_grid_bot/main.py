import time
import pandas as pd
from datetime import datetime

# Import project modules
import config
from utils import setup_logger
from state_manager import StateManager
from exchange_manager import ExchangeManager
from lrc_calculator import calculate_lrc_channel, get_price_at_index
from strategy import Strategy

class TradingBot:
    def __init__(self):
        self.logger = setup_logger(config.LOG_LEVEL)
        self.state_manager = StateManager(config.STATE_FILE_PATH, self.logger)
        self.exchange = ExchangeManager(
            config.API_KEY, config.API_SECRET, config.EXCHANGE_NAME, 
            config.SYMBOL, config.IS_TESTNET, self.logger
        )
        self.strategy = Strategy(config, lrc_calculator_module) # Pass the module itself
        self.inflection_timestamp = int(datetime.fromisoformat(config.INFLECTION_POINT_DATETIME.replace('Z', '+00:00')).timestamp())

    def run(self):
        self.logger.info("--- Starting LRC Grid Trading Bot ---")
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                self.logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
            
            self.logger.info(f"--- Cycle finished. Waiting for {config.LOOP_INTERVAL_SECONDS} seconds. ---")
            time.sleep(config.LOOP_INTERVAL_SECONDS)

    def run_cycle(self):
        """The main logic cycle for the bot."""
        self.logger.info("--- Starting new trading cycle ---")

        # 1. Fetch data and calculate LRC
        ohlcv_df = self.exchange.fetch_ohlcv(config.TIMEFRAME, config.LRC_LOOKBACK_CANDLES)
        if ohlcv_df.empty:
            self.logger.warning("Could not fetch OHLCV data. Skipping cycle.")
            return

        lrc_params = calculate_lrc_channel(ohlcv_df, self.inflection_timestamp)
        if not lrc_params:
            self.logger.warning("Could not calculate LRC parameters. Skipping cycle.")
            return

        # 2. Get current state and position from the exchange
        current_state = self.state_manager.get_state()
        live_position = self.exchange.get_current_position()
        
        # This is a simplified logic loop. A full implementation would need to handle:
        # - Syncing state with the live position from the exchange.
        # - Checking if existing orders have been filled.
        # - Managing the SSL time-based trigger.
        # - Managing the HSL price-based trigger.
        # - Placing/updating entry grid orders if no position.
        # - Placing/updating TP grid and stop orders if in a position.
        # - Handling the revoke logic after TPs are hit.

        # For this example, we'll just print the calculated values.
        self.print_status(ohlcv_df, lrc_params, current_state, live_position)

    def print_status(self, ohlcv_df, lrc_params, current_state, live_position):
        """Prints the current status of the bot and strategy."""
        latest_candle = ohlcv_df.iloc[-1]
        latest_price = latest_candle['close']
        latest_index = len(ohlcv_df) - 1

        self.logger.info(f"Latest Price: {latest_price}")
        self.logger.info(f"LRC Slope: {lrc_params['slope']:.4f}, Std Dev: {lrc_params['std_dev']:.2f}")

        # Get strategy direction
        direction, zones = self.strategy.get_trade_direction_and_zones(lrc_params)
        self.logger.info(f"Current Trend Direction: {direction.upper()}")

        # If no position, show potential entry grid
        if live_position['side'] == 'none':
            self.logger.info("Bot is FLAT. Analyzing potential entry grid...")
            entry_grid = self.strategy.generate_entry_grid(lrc_params, latest_index, direction, zones)
            if entry_grid:
                self.logger.info("--- Potential Entry Grid ---")
                for order in entry_grid:
                    self.logger.info(f"  - Price: {order['price']}, Amount: ${order['amount']}")
            else:
                self.logger.info("No favorable entry zone for the current direction.")
        else:
            # If in a position, show TP grid and stop losses
            self.logger.info(f"Bot is IN a {live_position['side'].upper()} position.")
            
            # Show TP Grid
            tp_grid = self.strategy.generate_tp_grid(lrc_params, latest_index, live_position['side'])
            self.logger.info("--- Potential Take-Profit Grid ---")
            for order in tp_grid:
                self.logger.info(f"  - Price: {order['price']}")

            # Show Stop Losses
            stop_prices = self.strategy.get_stop_loss_prices(lrc_params, latest_index, live_position['side'])
            self.logger.info("--- Stop Loss Levels ---")
            self.logger.info(f"  - SSL (4σ): {stop_prices.get('ssl_price')}")
            self.logger.info(f"  - HSL (5σ): {stop_prices.get('hsl_price')}")


if __name__ == '__main__':
    # We need to pass the lrc_calculator module to the Strategy class
    import lrc_calculator as lrc_calculator_module
    
    bot = TradingBot()
    bot.run() 