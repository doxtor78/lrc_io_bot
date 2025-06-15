# -*- coding: utf-8 -*-
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

# --- DataFeeder Logic ---
class DataFeeder:
    def __init__(self, db_path='data/market_data.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.data = {}

    def load_data(self, symbol, timeframe):
        table_name = f"{symbol.replace('/', '_')}_{timeframe}"
        try:
            df = pd.read_sql(table_name, self.engine, index_col='timestamp')
            print(f"Loaded {len(df)} records for {table_name}")
            df.index = pd.to_datetime(df.index)
            self.data[table_name] = df
            return df
        except Exception as e:
            print(f"Error loading data for {table_name}: {e}")
            return None

# --- TradingBot Logic ---
class TradingBot:
    def __init__(self, data, sma_window=50):
        self.data = data
        self.sma_window = sma_window
        self.signals = self._generate_signals()

    def _generate_signals(self):
        signals = pd.DataFrame(index=self.data.index)
        signals['price'] = self.data['close']
        signals['sma'] = self.data['close'].rolling(window=self.sma_window).mean()
        signals['signal'] = 0.0
        signals['signal'][self.sma_window:] = (signals['price'][self.sma_window:] > signals['sma'][self.sma_window:]).astype(float)
        signals['positions'] = signals['signal'].diff()
        return signals

# --- Backtester Logic ---
class Backtester:
    def __init__(self, initial_capital=10000.0):
        self.initial_capital = initial_capital

    def run(self, signals):
        portfolio = pd.DataFrame(index=signals.index)
        portfolio['price'] = signals['price']
        portfolio['signal'] = signals['signal']
        
        # When signal is 1, we are "in", when 0, we are "out"
        # This is a simplified cash-based backtest.
        positions = portfolio['signal'].diff().fillna(0)
        
        portfolio['cash'] = self.initial_capital - (positions * portfolio['price']).cumsum()
        portfolio['holdings_value'] = portfolio['signal'] * portfolio['price'] # Value of BTC if we hold it
        
        # This part is tricky. Let's simplify the portfolio value calculation.
        # We start with cash. When we buy, cash decreases. When we sell, cash increases.
        # The 'total' value is our cash plus the value of any holdings.
        
        # Let's try a clearer portfolio simulation
        portfolio['total'] = self.initial_capital
        
        # Create a 'holdings' column representing the number of units (e.g., BTC)
        portfolio['holdings'] = 0.0
        
        # Initial state
        portfolio.loc[portfolio.index[0], 'cash'] = self.initial_capital
        
        for i in range(1, len(portfolio)):
            prev_signal = portfolio['signal'].iloc[i-1]
            current_signal = portfolio['signal'].iloc[i]
            price = portfolio['price'].iloc[i]
            
            portfolio['cash'].iloc[i] = portfolio['cash'].iloc[i-1]
            portfolio['holdings'].iloc[i] = portfolio['holdings'].iloc[i-1]

            # Going "in"
            if current_signal == 1.0 and prev_signal == 0.0:
                portfolio['holdings'].iloc[i] = portfolio['cash'].iloc[i-1] / price
                portfolio['cash'].iloc[i] = 0.0

            # Going "out"
            elif current_signal == 0.0 and prev_signal == 1.0:
                portfolio['cash'].iloc[i] = portfolio['holdings'].iloc[i-1] * price
                portfolio['holdings'].iloc[i] = 0.0

        portfolio['total'] = portfolio['cash'] + (portfolio['holdings'] * portfolio['price'])
        
        return portfolio

    def plot_performance(self, portfolio, signals):
        plt.figure(figsize=(12, 8))
        
        ax1 = plt.subplot(2, 1, 1)
        portfolio['total'].plot(ax=ax1, label='Portfolio Value')
        ax1.set_title('Portfolio Performance')
        ax1.set_ylabel('Portfolio Value ($)')
        
        ax2 = plt.subplot(2, 1, 2, sharex=ax1)
        signals['price'].plot(ax=ax2, label='Price')
        signals['sma'].plot(ax=ax2, label='SMA', linestyle='--')
        
        ax2.plot(signals.loc[signals.positions == 1.0].index, 
                 signals.sma[signals.positions == 1.0],
                 '^', markersize=10, color='g', lw=0, label='Go In')
        ax2.plot(signals.loc[signals.positions == -1.0].index, 
                 signals.sma[signals.positions == -1.0],
                 'v', markersize=10, color='r', lw=0, label='Go Out')
                 
        ax2.set_title('Price and Trading Signals')
        ax2.set_ylabel('Price ($)')
        
        plt.tight_layout()
        plt.savefig('backtest_performance.png')
        print("\nBacktest performance plot saved to backtest_performance.png")

# --- Main Execution ---
if __name__ == '__main__':
    feeder = DataFeeder()
    btc_data = feeder.load_data('BTC/USDT', '1h')

    if btc_data is not None:
        bot = TradingBot(btc_data, sma_window=50)
        signals = bot.signals
        
        backtester = Backtester(initial_capital=10000.0)
        portfolio = backtester.run(signals)
        
        print("\n--- Backtest Results ---")
        print(f"Final Portfolio Value: ${portfolio['total'].iloc[-1]:.2f}")
        
        returns = portfolio['total'].pct_change()
        # Handle cases where standard deviation is zero
        if returns.std() != 0:
            sharpe_ratio = returns.mean() / returns.std() * (365*24)**0.5 # Annualized for hourly data
            print(f"Annualized Sharpe Ratio: {sharpe_ratio:.2f}")
        else:
            print("Sharpe Ratio: N/A (no variance in returns)")

        backtester.plot_performance(portfolio, signals)