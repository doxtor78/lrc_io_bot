import requests
import json
import time
import sqlite3
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple, Union
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('funding_rates.log'),
        logging.StreamHandler()
    ]
)

# Constants
EXCHANGES = {
    'binance': 'https://fapi.binance.com/fapi/v1/premiumIndex',
    'okx': 'https://www.okx.com/api/v5/public/mark-price?instId=BTC-USDT-SWAP',
    'bybit': 'https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT',
    'bitmex': 'https://www.bitmex.com/api/v1/instrument?symbol=XBTUSD&columns=fundingRate,lastPrice,markPrice',
    'kucoin': 'https://api-futures.kucoin.com/api/v1/contracts/active?symbol=BTCUSDTM',
    'gate': 'https://api.gateio.ws/api/v4/futures/usdt/contracts',
    'dydx': 'https://api.dydx.exchange/v3/markets',
}

# Add margin type mapping
MARGIN_TYPES = {
    'binance': 'USDT Margined',
    'okx': 'USDT Margined',
    'bybit': 'USDT Margined',
    'bitget': 'USDT Margined',
    'bitmex': 'Token Margined',
    'kucoin': 'USDT Margined',
    'gate': 'USDT Margined',
    'mexc': 'USDT Margined',
    'huobi': 'USDT Margined',
    'dydx': 'USDT Margined',
    'deribit': 'Token Margined',
    'kraken': 'USDT Margined',
    'coinglass': 'USDT Margined'  # Default to USDT for aggregated data
}

def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to standard BTC format."""
    # Remove common suffixes and prefixes
    symbol = symbol.upper()
    symbol = re.sub(r'[^A-Z0-9]', '', symbol)  # Remove special characters
    
    # Handle common BTC/XBT variations
    if symbol.startswith('XBT'):
        return 'BTC'
    elif symbol.startswith('BTC'):
        return 'BTC'
    
    return symbol

def get_funding_rate(exchange: str, symbol: str = 'BTC', max_retries: int = 3) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Get funding rate and price for a given exchange and symbol.
    Returns (funding_rate, price, error_message)
    """
    for attempt in range(max_retries):
        try:
            url = EXCHANGES[exchange]
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json'
            }
            
            if exchange == 'binance':
                response = requests.get(url, headers=headers)
                data = response.json()
                for item in data:
                    if item['symbol'] == f'{symbol}USDT':
                        price = float(item.get('markPrice', item.get('lastPrice', 0)))
                        return float(item['lastFundingRate']), price, None
                    
            elif exchange == 'okx':
                response = requests.get(url, headers=headers)
                data = response.json()
                if data.get('code') == '0':
                    price = float(data['data'][0].get('markPx', 0))
                    # Get funding rate from separate endpoint
                    funding_url = 'https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP'
                    funding_response = requests.get(funding_url, headers=headers)
                    funding_data = funding_response.json()
                    if funding_data.get('code') == '0':
                        return float(funding_data['data'][0]['fundingRate']), price, None
                    
            elif exchange == 'bybit':
                response = requests.get(url, headers=headers)
                data = response.json()
                if data['retCode'] == 0 and data['result']['list']:
                    item = data['result']['list'][0]
                    price = float(item.get('lastPrice', item.get('markPrice', item.get('indexPrice', 0))))
                    # Get funding rate from a separate endpoint
                    funding_url = 'https://api.bybit.com/v5/market/funding/history'
                    funding_params = {'category': 'linear', 'symbol': f'{symbol}USDT'}
                    funding_response = requests.get(funding_url, params=funding_params, headers=headers)
                    funding_data = funding_response.json()
                    if funding_data['retCode'] == 0 and funding_data['result']['list']:
                        return float(funding_data['result']['list'][0]['fundingRate']), price, None
                    
            elif exchange == 'bitmex':
                response = requests.get(url, headers=headers, timeout=10)
                data = response.json()
                if data and len(data) > 0:
                    price = float(data[0].get('markPrice', data[0].get('lastPrice', data[0].get('indexPrice', 0))))
                    return float(data[0]['fundingRate']), price, None
                    
            elif exchange == 'kucoin':
                response = requests.get(url, headers=headers)
                data = response.json()
                if data.get('code') == '200000':
                    for item in data.get('data', []):
                        price = float(item.get('markPrice', item.get('lastTradePrice', item.get('indexPrice', 0))))
                        return float(item['fundingFeeRate']), price, None
                    
            elif exchange == 'gate':
                response = requests.get(url, headers=headers)
                data = response.json()
                for item in data:
                    if item['name'] == f'{symbol}_USDT':
                        price = float(item.get('mark_price', item.get('last_price', item.get('index_price', 0))))
                        return float(item['funding_rate']), price, None
                    
            elif exchange == 'dydx':
                response = requests.get(url, headers=headers)
                data = response.json()
                for market in data.get('markets', {}).values():
                    if market['market'] == f'{symbol}-USD':
                        price = float(market.get('oraclePrice', market.get('indexPrice', market.get('markPrice', 0))))
                        return float(market['nextFundingRate']), price, None
                    
            return None, None, f"No data found for {symbol} on {exchange}"
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retrying
                continue
            return None, None, f"Network error: {str(e)}"
        except (KeyError, ValueError, TypeError) as e:
            return None, None, f"Data parsing error: {str(e)}"
        except Exception as e:
            return None, None, f"Unexpected error: {str(e)}"

def update_funding_rates():
    """Update funding rates for all exchanges and symbols."""
    conn = sqlite3.connect('funding_rates.db')
    cur = conn.cursor()
    
    # Create table if it doesn't exist
    cur.execute('''
        CREATE TABLE IF NOT EXISTS funding_rates (
            timestamp DATETIME,
            exchange TEXT,
            symbol TEXT,
            rate REAL,
            price REAL,
            margin_type TEXT,
            PRIMARY KEY (timestamp, exchange, symbol)
        )
    ''')
    
    timestamp = datetime.utcnow()
    
    for exchange in EXCHANGES:
        try:
            # Get funding rate for BTC
            rate, price, error = get_funding_rate(exchange, 'BTC')
            
            if rate is not None and price is not None:
                margin_type = MARGIN_TYPES.get(exchange, 'USDT Margined')
                cur.execute('''
                    INSERT OR REPLACE INTO funding_rates 
                    (timestamp, exchange, symbol, rate, price, margin_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp, exchange, 'BTC', rate, price, margin_type))
                logging.info(f"Updated {exchange} BTC: {rate:.6f} @ ${price:.2f}")
            else:
                logging.error(f"Error fetching {exchange} BTC: {error}")
                
        except Exception as e:
            logging.error(f"Error processing {exchange}: {str(e)}")
            
    conn.commit()
    conn.close()

def get_latest_rates() -> Dict[str, Dict[str, float]]:
    """Get latest funding rates for all exchanges and symbols."""
    conn = sqlite3.connect('funding_rates.db')
    cur = conn.cursor()
    
    cur.execute('''
        SELECT exchange, symbol, rate, price, margin_type
        FROM funding_rates
        WHERE timestamp >= datetime('now', '-5 minutes')
        ORDER BY timestamp DESC
    ''')
    
    rates = {}
    for row in cur.fetchall():
        exchange, symbol, rate, price, margin_type = row
        if margin_type not in rates:
            rates[margin_type] = {}
        rates[margin_type][exchange] = {
            'rate': rate,
            'price': price
        }
    
    conn.close()
    return rates

def get_historical_rates(symbol: str = 'BTC', hours: int = 24) -> List[Dict]:
    """Get historical funding rates for a symbol."""
    conn = sqlite3.connect('funding_rates.db')
    cur = conn.cursor()
    
    cur.execute('''
        SELECT timestamp, exchange, rate, price, margin_type
        FROM funding_rates
        WHERE symbol = ? AND timestamp >= datetime('now', ? || ' hours')
        ORDER BY timestamp DESC
    ''', (symbol, -hours))
    
    rates = []
    for row in cur.fetchall():
        timestamp, exchange, rate, price, margin_type = row
        rates.append({
            'timestamp': timestamp,
            'exchange': exchange,
            'rate': rate,
            'price': price,
            'margin_type': margin_type
        })
    
    conn.close()
    return rates

def init_db(check_same_thread=True):
    """Initialize the SQLite database connection."""
    conn = sqlite3.connect('funding_rates.db', check_same_thread=check_same_thread)
    cur = conn.cursor()
    
    # Create table if it doesn't exist
    cur.execute('''
        CREATE TABLE IF NOT EXISTS funding_rates (
            timestamp DATETIME,
            exchange TEXT,
            symbol TEXT,
            rate REAL,
            price REAL,
            margin_type TEXT,
            PRIMARY KEY (timestamp, exchange, symbol)
        )
    ''')
    
    conn.commit()
    return conn

def scrape_funding_rates() -> List[Dict]:
    """Scrape funding rates from all exchanges."""
    funding_data = []
    timestamp = datetime.utcnow()
    
    for exchange in EXCHANGES:
        try:
            rate, price, error = get_funding_rate(exchange, 'BTC')
            if rate is not None and price is not None:
                funding_data.append({
                    'timestamp': timestamp,
                    'exchange': exchange,
                    'symbol': 'BTC',
                    'rate': rate,
                    'price': price,
                    'margin_type': MARGIN_TYPES.get(exchange, 'USDT Margined')
                })
                logging.info(f"Updated {exchange} BTC: {rate:.6f} @ ${price:.2f}")
            else:
                logging.error(f"Error fetching {exchange} BTC: {error}")
        except Exception as e:
            logging.error(f"Error processing {exchange}: {str(e)}")
            
    return funding_data

def save_to_db(conn: sqlite3.Connection, funding_data: List[Dict]) -> None:
    """Save funding rates data to the database."""
    cur = conn.cursor()
    
    for data in funding_data:
        cur.execute('''
            INSERT OR REPLACE INTO funding_rates 
            (timestamp, exchange, symbol, rate, price, margin_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['timestamp'],
            data['exchange'],
            data['symbol'],
            data['rate'],
            data['price'],
            data['margin_type']
        ))
    
    conn.commit()

if __name__ == '__main__':
    update_funding_rates() 