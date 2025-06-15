import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv('BYBIT_TESTNET_API_KEY')
API_SECRET = os.getenv('BYBIT_TESTNET_API_SECRET')

# Trading Parameters
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
POSITION_SIZE = float(os.getenv('POSITION_SIZE', '0.001'))
LEVERAGE = int(os.getenv('LEVERAGE', '1'))

# API Endpoints
TESTNET_URL = "https://api-testnet.bybit.com"

# Validation
if not API_KEY or not API_SECRET:
    raise ValueError("API credentials not found in environment variables") 