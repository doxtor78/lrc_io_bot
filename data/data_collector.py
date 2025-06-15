import ccxt
import pandas as pd
import os
from sqlalchemy import create_engine, inspect

def fetch_data(exchange, symbol, timeframe, limit):
    """Fetches historical data from the specified exchange."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def save_to_db(df, symbol, timeframe):
    """Saves a DataFrame to a SQLite database."""
    db_path = 'data/market_data.db'
    engine = create_engine(f'sqlite:///{db_path}')
    table_name = f"{symbol.replace('/', '_')}_{timeframe}"
    
    df_with_index = df.set_index('timestamp')

    # Check if table exists
    inspector = inspect(engine)
    if inspector.has_table(table_name):
        # Append new data, ignoring duplicates if any
        existing_df = pd.read_sql(table_name, engine, index_col='timestamp')
        combined_df = pd.concat([existing_df, df_with_index])
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        combined_df.to_sql(table_name, engine, if_exists='replace', index=True)
        print(f"Appended data to table {table_name} in {db_path}")
    else:
        # Create new table
        df_with_index.to_sql(table_name, engine, if_exists='replace', index=True)
        print(f"Created table {table_name} in {db_path}")


def main():
    """Main function to run the data collection."""
    exchange = ccxt.binance()
    symbol = 'BTC/USDT'
    timeframe = '1h' # 1-hour candles
    limit = 1000 # Number of candles to fetch

    print(f"Fetching {limit} {timeframe} candles for {symbol} from {exchange.id}...")
    df = fetch_data(exchange, symbol, timeframe, limit)

    if df is not None and not df.empty:
        print(f"Successfully fetched {len(df)} data points.")
        # Ensure data directory exists
        if not os.path.exists('data'):
            os.makedirs('data')
        save_to_db(df, symbol, timeframe)
    else:
        print("Could not fetch data.")

if __name__ == "__main__":
    main() 