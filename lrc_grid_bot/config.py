# --- Exchange & API ---
EXCHANGE_NAME = 'bitmex' # or 'bybit', 'binance', etc.
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
IS_TESTNET = True

# --- Market ---
SYMBOL = 'XBTUSD' # BitMEX symbol for BTC/USD perpetual contract
TIMEFRAME = '1h'

# --- LRC Strategy Parameters ---
INFLECTION_POINT_DATETIME = '2023-01-01T00:00:00Z' # ISO 8601 format
LRC_LOOKBACK_CANDLES = 200 # Number of candles to use for regression calculation

# --- Grid Trading Parameters ---
MAIN_ORDER_SIZE_USD = 1000 # Total size of the position in USD
SUB_ORDER_COUNT = 5      # The number of grid orders to place (5 for entry, 5 for TP)

# --- Risk Management Parameters ---
# Favorable zones for trading based on trend direction
UPTREND_FAVORABLE_ZONES = {'long': (-1.0, -3.0), 'short': (2.0, 3.0)}
DOWNTREND_FAVORABLE_ZONES = {'short': (1.0, 3.0), 'long': (-2.0, -3.0)}

# Take profit target zones
TAKE_PROFIT_ZONES = {'long': (0.0, 3.0), 'short': (0.0, -3.0)}

# Stop Loss Levels (in standard deviations)
SSL_LEVEL = 4.0
HSL_LEVEL = 5.0

# Time delay in seconds for the Soft Stop Loss trigger
SSL_TIME_DELAY_SECONDS = 1800 # 30 minutes

# --- Operational Parameters ---
LOOP_INTERVAL_SECONDS = 60 # How often the main bot loop runs
STATE_FILE_PATH = 'lrc_grid_bot/state.json'
LOG_LEVEL = 'INFO' 