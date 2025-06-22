import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import numpy as np

# --- LRC Calculation Logic (from stable_v3/lrc_calculator.py) ---
def calculate_lrc_parameters(data, use_date_range=False, start_timestamp=None):
    """
    Calculates the key parameters of a Linear Regression Channel.
    """
    if not isinstance(data, list) or not data:
        # If data is a DataFrame, convert it to list of dicts
        if isinstance(data, pd.DataFrame):
            data = data.to_dict('records')
        else:
            return {}

    # --- 1. Filter Data by Date Range ---
    first_valid_bar_index = 0
    if use_date_range and start_timestamp:
        for i, d in enumerate(data):
            if d['time'] >= start_timestamp:
                first_valid_bar_index = i
                break
        else:
            return {}
    
    calc_data = data[first_valid_bar_index:]
    
    if len(calc_data) < 2:
        return {}

    # --- 2. Perform Linear Regression against BAR INDEX ---
    source_prices = np.array([d['close'] for d in calc_data])
    indices = np.arange(len(source_prices))
    slope, intercept = np.polyfit(indices, source_prices, 1)

    # --- 3. Calculate Standard Deviation ---
    regression_values = slope * indices + intercept
    deviations = source_prices - regression_values
    std_dev = np.std(deviations)

    # --- 4. Return the essential parameters ---
    start_point_index = 0
    end_point_index = len(indices) - 1

    start_price = slope * start_point_index + intercept
    end_price = slope * end_point_index + intercept
    
    # Ensure time is in the correct format (pd.Timestamp to unix)
    start_time_val = calc_data[start_point_index]['time']
    end_time_val = calc_data[end_point_index]['time']

    if isinstance(start_time_val, pd.Timestamp):
        start_time = int(start_time_val.timestamp())
    else:
        start_time = start_time_val

    if isinstance(end_time_val, pd.Timestamp):
        end_time = int(end_time_val.timestamp())
    else:
        end_time = end_time_val
        
    return {
        'start_time': start_time,
        'start_price': start_price,
        'end_time': end_time,
        'end_price': end_price,
        'std_dev': std_dev,
        'slope': slope,
        'intercept': intercept
    }

# --- DataFeeder Logic (from In-and-outbot/backtester.py) ---
class DataFeeder:
    def __init__(self, db_path='In-and-outbot/data/market_data.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.data = {}

    def load_data(self, symbol, timeframe):
        table_name = f"{symbol.replace('/', '_')}_{timeframe}"
        try:
            # Load data and set the index to 'timestamp'
            df = pd.read_sql(f'SELECT * FROM "{table_name}"', self.engine)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            print(f"Loaded {len(df)} records for {table_name}")
            self.data[table_name] = df
            return df
        except Exception as e:
            print(f"Error loading data for {table_name}: {e}")
            return None

# --- New TradingBot Logic (LRC Strategy) ---
class TradingBot:
    def __init__(self, data, deviation=1.0):
        self.data = data
        self.deviation = deviation
        # The 'time' column for calculation needs to be unix timestamp
        data_for_lrc = self.data.reset_index()
        data_for_lrc['time'] = data_for_lrc['timestamp'].apply(lambda x: int(x.timestamp()))
        self.lrc_params = calculate_lrc_parameters(data_for_lrc.to_dict('records'))
        self.signals = self._generate_signals()

    def _generate_signals(self):
        if not self.lrc_params:
            print("Could not generate signals: LRC parameters not calculated.")
            return pd.DataFrame()

        slope = self.lrc_params['slope']
        intercept = self.lrc_params['intercept']
        std_dev = self.lrc_params['std_dev']

        indices = np.arange(len(self.data))
        lrc_center = slope * indices + intercept
        lrc_upper = lrc_center + self.deviation * std_dev
        lrc_lower = lrc_center - self.deviation * std_dev

        signals = pd.DataFrame(index=self.data.index)
        signals['price'] = self.data['close']
        signals['lrc_upper'] = lrc_upper
        signals['lrc_lower'] = lrc_lower
        signals['signal'] = 0.0  # 0 for out, 1 for in

        position = 0
        for i in range(len(signals)):
            if position == 0 and self.data['low'].iloc[i] < signals['lrc_lower'].iloc[i]:
                position = 1
            elif position == 1 and self.data['high'].iloc[i] > signals['lrc_upper'].iloc[i]:
                position = 0
            signals['signal'].iloc[i] = position

        signals['positions'] = signals['signal'].diff().fillna(0)
        return signals

# --- Backtester Logic (from In-and-outbot/backtester.py) ---
class Backtester:
    def __init__(self, initial_capital=10000.0):
        self.initial_capital = initial_capital

    def run(self, signals):
        if signals.empty:
            print("Cannot run backtest on empty signals.")
            return pd.DataFrame()
        
        portfolio = pd.DataFrame(index=signals.index)
        portfolio['price'] = signals['price']
        portfolio['signal'] = signals['signal']
        portfolio['cash'] = self.initial_capital
        portfolio['holdings'] = 0.0
        
        portfolio.loc[portfolio.index[0], 'cash'] = self.initial_capital

        for i in range(1, len(portfolio)):
            prev_signal = portfolio['signal'].iloc[i-1]
            current_signal = portfolio['signal'].iloc[i]
            price = portfolio['price'].iloc[i]
            
            portfolio['cash'].iloc[i] = portfolio['cash'].iloc[i-1]
            portfolio['holdings'].iloc[i] = portfolio['holdings'].iloc[i-1]

            if current_signal > prev_signal: # Buy signal
                portfolio['holdings'].iloc[i] = portfolio['cash'].iloc[i-1] / price
                portfolio['cash'].iloc[i] = 0.0

            elif current_signal < prev_signal: # Sell signal
                portfolio['cash'].iloc[i] = portfolio['holdings'].iloc[i-1] * price
                portfolio['holdings'].iloc[i] = 0.0

        portfolio['total'] = portfolio['cash'] + (portfolio['holdings'] * portfolio['price'])
        return portfolio

    def plot_performance(self, portfolio, signals):
        if portfolio.empty or signals.empty:
            print("Cannot plot performance for empty portfolio or signals.")
            return
            
        plt.figure(figsize=(12, 8))
        
        ax1 = plt.subplot(2, 1, 1)
        portfolio['total'].plot(ax=ax1, label='Portfolio Value')
        ax1.set_title('LRC Strategy Portfolio Performance')
        ax1.set_ylabel('Portfolio Value ($)')
        
        ax2 = plt.subplot(2, 1, 2, sharex=ax1)
        signals['price'].plot(ax=ax2, label='Price')
        signals['lrc_upper'].plot(ax=ax2, label='Upper LRC', linestyle='--', color='red')
        signals['lrc_lower'].plot(ax=ax2, label='Lower LRC', linestyle='--', color='green')
        
        buy_signals = signals[signals.positions == 1.0]
        sell_signals = signals[signals.positions == -1.0]

        ax2.plot(buy_signals.index, signals.loc[buy_signals.index]['lrc_lower'], '^', markersize=10, color='g', lw=0, label='Go In')
        ax2.plot(sell_signals.index, signals.loc[sell_signals.index]['lrc_upper'], 'v', markersize=10, color='r', lw=0, label='Go Out')
                 
        ax2.set_title('Price and Trading Signals')
        ax2.set_ylabel('Price ($)')
        
        plt.tight_layout()
        plt.savefig('lrc_io_backtest.png')
        print("\nBacktest performance plot saved to lrc_io_backtest.png")

# --- Main Execution ---
if __name__ == '__main__':
    feeder = DataFeeder()
    btc_data = feeder.load_data('BTC/USDT', '1h')

    if btc_data is not None and not btc_data.empty:
        bot = TradingBot(btc_data, deviation=2.0) # Using 2 std deviations
        signals = bot.signals
        
        backtester = Backtester(initial_capital=10000.0)
        portfolio = backtester.run(signals)
        
        if not portfolio.empty:
            print("\n--- LRC Strategy Backtest Results ---")
            print(f"Final Portfolio Value: ${portfolio['total'].iloc[-1]:.2f}")
            
            returns = portfolio['total'].pct_change().dropna()
            if returns.std() != 0:
                sharpe_ratio = returns.mean() / returns.std() * (365*24)**0.5
                print(f"Annualized Sharpe Ratio: {sharpe_ratio:.2f}")
            else:
                print("Sharpe Ratio: N/A (no variance in returns)")

            backtester.plot_performance(portfolio, signals)
    else:
        print("Could not load data for backtesting.") 