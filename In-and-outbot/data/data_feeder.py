import pandas as pd
from sqlalchemy import create_engine

class DataFeeder:
    def __init__(self, db_path='data/market_data.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.data = {}

    def load_data(self, symbol, timeframe):
        """Loads data for a specific symbol and timeframe from the database."""
        table_name = f"{symbol.replace('/', '_')}_{timeframe}"
        try:
            self.data[table_name] = pd.read_sql(table_name, self.engine, index_col='timestamp')
            print(f"Loaded {len(self.data[table_name])} records for {table_name}")
            return self.data[table_name]
        except Exception as e:
            print(f"Error loading data for {table_name}: {e}")
            return None

    def get_data(self, symbol, timeframe):
        """Returns the loaded data for a symbol and timeframe."""
        table_name = f"{symbol.replace('/', '_')}_{timeframe}"
        return self.data.get(table_name)

if __name__ == '__main__':
    # Example usage:
    feeder = DataFeeder()
    btc_data = feeder.load_data('BTC/USDT', '1h')
    if btc_data is not None:
        print("Data loaded successfully:")
        print(btc_data.head())