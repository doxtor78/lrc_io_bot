import requests
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import ccxt
import argparse
from lrc_calculator import calculate_lrc

def fetch_binance_data(api_key, api_secret, symbol='BTC/USDT', timeframe='1h', limit=1000):
    """Fetches historical candlestick data from Binance using ccxt."""
    print(f"Connecting to Binance...")
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,  # Respect API rate limits
    })
    
    try:
        print(f"Fetching {limit} {timeframe} candles for {symbol} from Binance...")
        # fetch_ohlcv returns: [timestamp, open, high, low, close, volume]
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # Convert to the dictionary format our other functions expect
        candles = [{
            'time': int(bar[0] / 1000),  # Convert millisecond timestamp to seconds
            'open': float(bar[1]),
            'high': float(bar[2]),
            'low': float(bar[3]),
            'close': float(bar[4])
        } for bar in ohlcv]
        
        print("Successfully fetched data from Binance.")
        return candles
    except Exception as e:
        print(f"Error fetching Binance data: {e}")
        return None

def plot_lrc_chart(candles, lrc_results, deviations, output_filename='lrc_chart.png'):
    """Plots the candlestick data and LRC on a chart and saves it."""
    
    times = [datetime.datetime.fromtimestamp(c['time']) for c in candles]
    close_prices = [c['close'] for c in candles]

    fig, ax = plt.subplots(figsize=(15, 8))

    # Plot the closing price line
    ax.plot(times, close_prices, label='Close Price', color='black', linewidth=0.8)

    if lrc_results:
        baseline = lrc_results['baseline']
        std_dev = lrc_results['std_dev']
        
        # Plot the LRC baseline
        lrc_times = [datetime.datetime.fromtimestamp(p['time']) for p in baseline]
        lrc_values = [p['value'] for p in baseline]
        ax.plot(lrc_times, lrc_values, label='LRC Baseline', color='blue', linestyle='--')

        # Define colors for deviation channels for better visualization
        dev_colors = {1.0: '#ffcccc', 2.0: '#ff9999', 3.0: '#ff6666', 4.0: '#ff3333'}
        
        # Plot the deviation channels
        for dev in sorted(deviations, reverse=True):
            upper_channel = [p['value'] + dev * std_dev for p in baseline]
            lower_channel = [p['value'] - dev * std_dev for p in baseline]
            
            # Use fill_between to create the channel area
            ax.fill_between(lrc_times, upper_channel, lower_channel, 
                            color=dev_colors.get(dev, 'gray'), alpha=0.3, label=f'±{dev}σ')

    ax.set_title('Linear Regression Channel Chart (XBTUSD 1h)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price (USD)')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.6)

    # Format the date on the x-axis for better readability
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    fig.autofmt_xdate()
    
    plt.tight_layout()
    plt.savefig(output_filename)
    print(f"\nChart successfully saved to {output_filename}")


if __name__ == "__main__":
    # !!! --- SECURITY WARNING --- !!!
    # The API keys below were provided for a temporary session.
    # For your security, please REVOKE these keys from your Binance account now.
    # In real applications, use environment variables or a secure vault for API keys.
    BINANCE_API_KEY = "8qaM9QUg28LHutP1Kaz0OUsH3vJNIAbEZZKc9diIjp851gK4fb90uRDXH4Nz4Us7"
    BINANCE_SECRET_KEY = "jjZCYNpdSXOeDPyt72PH5hnbimikM5WaTZpAdgDCbbSDZDW20NxpVzEhqM06jMaO"

    # 1. --- Configuration ---
    parser = argparse.ArgumentParser(description="Generate a Linear Regression Channel chart from Binance data.")
    parser.add_argument(
        '--start_date',
        type=str,
        default="2024-06-10 21:00:00",
        help='The start date for the LRC calculation in "YYYY-MM-DD HH:MM:SS" format.'
    )
    args = parser.parse_args()
    start_date_str = args.start_date
    
    try:
        start_datetime_obj = datetime.datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
        start_timestamp_utc = int(start_datetime_obj.timestamp())
    except ValueError:
        print(f"Error: Invalid date format for '{start_date_str}'. Please use 'YYYY-MM-DD HH:MM:SS'.")
        exit()
    
    # These are the deviation levels to calculate and plot
    deviations_to_plot = [1.0, 2.0, 3.0, 4.0]

    # 2. --- Fetch Data ---
    candle_data = fetch_binance_data(
        api_key=BINANCE_API_KEY, 
        api_secret=BINANCE_SECRET_KEY,
        symbol='BTC/USDT', 
        timeframe='1h', 
        limit=1000
    )

    if candle_data:
        # 3. --- Calculate LRC ---
        print(f"Calculating Linear Regression Channel starting from {start_date_str} UTC...")
        lrc_data = calculate_lrc(candle_data, use_date_range=True, start_timestamp=start_timestamp_utc)

        # 4. --- Plot Chart ---
        if lrc_data:
            print("Plotting chart...")
            
            # Filter the candles to only include the ones used in the LRC calculation for a cleaner plot
            lrc_start_time = lrc_data['start_bar_time']
            chart_candles = [c for c in candle_data if c['time'] >= lrc_start_time]

            plot_lrc_chart(chart_candles, lrc_data, deviations_to_plot, output_filename='lrc_chart.png')
        else:
            print("\nCould not calculate LRC. This might be because there is no data available after your specified start date in the fetched range.") 