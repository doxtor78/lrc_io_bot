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
            # Use a full SQL query for robustness
            df = pd.read_sql(f"SELECT * FROM {table_name}", self.engine, index_col='timestamp')
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
        self.data = None

    def run(self, signals, data):
        self.data = data
        portfolio = signals.copy()
        portfolio['cash'] = 0.0
        portfolio['holdings'] = 0.0
        portfolio['total'] = 0.0

        # Start with initial capital
        portfolio.iloc[0, portfolio.columns.get_loc('cash')] = self.initial_capital
        portfolio.iloc[0, portfolio.columns.get_loc('total')] = self.initial_capital
        
        status = 'OUT'
        limit_order_price = 0.0

        for i in range(1, len(portfolio)):
            # --- Carry over portfolio from previous timestamp ---
            portfolio.iloc[i, portfolio.columns.get_loc('cash')] = portfolio.iloc[i-1, portfolio.columns.get_loc('cash')]
            portfolio.iloc[i, portfolio.columns.get_loc('holdings')] = portfolio.iloc[i-1, portfolio.columns.get_loc('holdings')]
            
            # --- Get current market data ---
            price = portfolio.price.iloc[i]
            high_price = self.data.high.iloc[i]
            go_in_signal = portfolio.positions.iloc[i] == 1.0
            go_out_signal = portfolio.positions.iloc[i] == -1.0

            # --- State Machine Logic ---
            if status == 'OUT':
                if go_in_signal:
                    status = 'IN'
                    amount_to_buy = portfolio.cash.iloc[i-1] / price
                    portfolio.iloc[i, portfolio.columns.get_loc('holdings')] = amount_to_buy
                    portfolio.iloc[i, portfolio.columns.get_loc('cash')] = 0.0
                    print(f"{portfolio.index[i].date()}: GO IN @ {price:.2f}")

            elif status == 'IN':
                if go_out_signal:
                    status = 'WANTS_TO_EXIT'
                    limit_order_price = price
                    print(f"{portfolio.index[i].date()}: WANTS TO EXIT. Limit Sell @ {limit_order_price:.2f}")

            elif status == 'WANTS_TO_EXIT':
                if high_price >= limit_order_price:
                    status = 'OUT'
                    cash_from_sale = portfolio.holdings.iloc[i-1] * limit_order_price
                    portfolio.iloc[i, portfolio.columns.get_loc('cash')] = cash_from_sale
                    portfolio.iloc[i, portfolio.columns.get_loc('holdings')] = 0.0
                    print(f"{portfolio.index[i].date()}: EXIT CONFIRMED @ {limit_order_price:.2f}")
                    limit_order_price = 0.0
                else:
                    # Chase the price
                    limit_order_price = price
                    print(f"{portfolio.index[i].date()}: CHASING EXIT. New Limit @ {limit_order_price:.2f}")

            # --- Update total portfolio value for the current timestamp ---
            portfolio.iloc[i, portfolio.columns.get_loc('total')] = portfolio.cash.iloc[i] + (portfolio.holdings.iloc[i] * price)

        return portfolio

    def plot_performance(self, portfolio, signals):
        plt.figure(figsize=(12, 8))
        
        ax1 = plt.subplot(2, 1, 1)
        portfolio['total'].plot(ax=ax1, label='Portfolio Value')
        ax1.set_title('Portfolio Performance (with Limit Order Simulation)')
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
        portfolio = backtester.run(signals, btc_data)
        
        print("\n--- Backtest Results (with Limit Order Simulation) ---")
        print(f"Final Portfolio Value: ${portfolio['total'].iloc[-1]:.2f}")
        
        returns = portfolio['total'].pct_change()
        if returns.std() != 0:
            sharpe_ratio = returns.mean() / returns.std() * (365*24)**0.5
            print(f"Annualized Sharpe Ratio: {sharpe_ratio:.2f}")
        else:
            print("Sharpe Ratio: N/A (no variance in returns)")

        backtester.plot_performance(portfolio, signals)