import ccxt
import pandas as pd
from typing import List, Dict, Any

class ExchangeManager:
    def __init__(self, api_key: str, api_secret: str, exchange_name: str, symbol: str, is_testnet: bool, logger):
        self.logger = logger
        self.symbol = symbol
        
        try:
            exchange_class = getattr(ccxt, exchange_name)
            self.exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
            if is_testnet:
                self.exchange.set_sandbox_mode(True)
            self.logger.info(f"Successfully connected to {exchange_name} (Testnet: {is_testnet})")
        except AttributeError:
            self.logger.error(f"Exchange '{exchange_name}' not found in ccxt.")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing exchange: {e}")
            raise

    def fetch_ohlcv(self, timeframe: str, limit: int) -> pd.DataFrame:
        """Fetches OHLCV data and returns it as a pandas DataFrame."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # Ensure timestamp is in UTC if timezone info is present
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            self.logger.info(f"Fetched {len(df)} candles for {self.symbol} on {timeframe} timeframe.")
            return df
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data: {e}")
            return pd.DataFrame()

    def get_current_position(self) -> Dict[str, Any]:
        """Fetches the current position for the bot's symbol."""
        try:
            # ccxt unified method for fetching positions
            positions = self.exchange.fetch_positions([self.symbol])
            if positions:
                # Filter for the specific symbol, as fetch_positions can return multiple
                position = next((p for p in positions if p['symbol'] == self.symbol), None)
                if position and position.get('contracts', 0) != 0:
                    return {
                        'side': position.get('side'),
                        'size_contracts': position.get('contracts'),
                        'entry_price': position.get('entryPrice')
                    }
            return {'side': 'none', 'size_contracts': 0.0, 'entry_price': 0.0}
        except Exception as e:
            self.logger.error(f"Error fetching current position: {e}")
            return {'side': 'none', 'size_contracts': 0.0, 'entry_price': 0.0}
            
    def place_limit_order(self, side: str, amount: float, price: float, reduce_only: bool = False) -> Dict[str, Any]:
        """Places a single limit order."""
        try:
            params = {'reduceOnly': reduce_only}
            order = self.exchange.create_limit_order(self.symbol, side, amount, price, params=params)
            self.logger.info(f"Placed {side} limit order for {amount} {self.symbol} at {price}. ReduceOnly: {reduce_only}")
            return order
        except Exception as e:
            self.logger.error(f"Error placing limit order: {e}")
            return {}

    def place_market_order(self, side: str, amount: float, reduce_only: bool = False) -> Dict[str, Any]:
        """Places a single market order (for HSL)."""
        try:
            params = {'reduceOnly': reduce_only}
            order = self.exchange.create_market_order(self.symbol, side, amount, params=params)
            self.logger.warning(f"Placed EMERGENCY {side} market order for {amount} {self.symbol}. ReduceOnly: {reduce_only}")
            return order
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return {}

    def cancel_order(self, order_id: str):
        """Cancels a single order by its ID."""
        try:
            self.exchange.cancel_order(order_id, self.symbol)
            self.logger.info(f"Successfully cancelled order {order_id}")
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")

    def cancel_all_orders(self):
        """Cancels all open orders for the symbol."""
        try:
            self.exchange.cancel_all_orders(self.symbol)
            self.logger.info(f"Cancelled all open orders for {self.symbol}.")
        except Exception as e:
            self.logger.error(f"Error cancelling all orders: {e}") 