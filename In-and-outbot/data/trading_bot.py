import pandas as pd

class TradingBot:
    def __init__(self, data, sma_window=50):
        self.data = data
        self.sma_window = sma_window
        self.signals = self._generate_signals()

    def _calculate_sma(self, window):
        """Calculates the Simple Moving Average (SMA)."""
        return self.data['close'].rolling(window=window).mean()

    def _generate_signals(self):
        """
        Generates trading signals based on a simple SMA crossover strategy.
        - 'in' (Buy) when the closing price is above the SMA.
        - 'out' (Sell) when the closing price is below the SMA.
        """
        signals = pd.DataFrame(index=self.data.index)
        signals['signal'] = 0.0
        
        # Calculate SMA
        sma = self._calculate_sma(self.sma_window)
        
        # Create signals
        signals['price'] = self.data['close']
        signals['sma'] = sma
        signals['signal'][self.sma_window:] = \
            (signals['price'][self.sma_window:] > signals['sma'][self.sma_window:]).astype(float)
        
        # Generate trading orders
        signals['positions'] = signals['signal'].diff()
        
        return signals

    def get_signals(self):
        return self.signals

if __name__ == '__main__':
    # This is a placeholder for testing the bot with data.
    # We will integrate this with the DataFeeder and a backtester next.
    
    # Create a dummy DataFrame for testing
    data = {'close': [100, 102, 105, 103, 99, 98, 101, 104, 107, 110]}
    dummy_df = pd.DataFrame(data)
    
    bot = TradingBot(dummy_df, sma_window=3) # Pass window size during instantiation
    signals = bot.get_signals()
    
    print("Generated Signals:")
    print(signals.head(10))