import numpy as np
import pandas as pd

def calculate_lrc_channel(df_ohlcv: pd.DataFrame, inflection_timestamp: int):
    """
    Calculates the parameters of a Linear Regression Channel based on closing prices.

    Args:
        df_ohlcv (pd.DataFrame): DataFrame with 'timestamp', 'open', 'high', 'low', 'close', 'volume'.
                                 Timestamp should be in milliseconds.
        inflection_timestamp (int): The Unix timestamp (in seconds) from which to start the calculation.

    Returns:
        dict: A dictionary containing the LRC parameters:
              'slope', 'intercept', 'std_dev'. Returns an empty dict if calculation fails.
    """
    if df_ohlcv.empty:
        return {}

    # Convert inflection point from seconds to milliseconds for comparison
    inflection_ms = inflection_timestamp * 1000
    
    # Filter data to start from the inflection point
    calc_data = df_ohlcv[df_ohlcv['timestamp'] >= inflection_ms].copy()

    if len(calc_data) < 2:
        return {} # Not enough data points for regression

    # Use a simple range of integers as the independent variable (x-axis)
    indices = np.arange(len(calc_data))
    source_prices = calc_data['close'].values

    # Perform linear regression
    try:
        slope, intercept = np.polyfit(indices, source_prices, 1)
    except np.linalg.LinAlgError:
        return {} # Failed to converge

    # Calculate the regression line values for each point
    regression_values = slope * indices + intercept

    # Calculate the deviations from the regression line
    deviations = source_prices - regression_values

    # Calculate the standard deviation of these deviations
    std_dev = np.std(deviations)
    
    if std_dev == 0:
        return {} # Avoid division by zero if all prices are on the line

    return {
        'slope': slope,
        'intercept': intercept,
        'std_dev': std_dev
    }

def get_price_at_index(lrc_params: dict, index: int, std_dev_multiplier: float = 0.0):
    """
    Calculates the expected price at a specific index in the regression channel.

    Args:
        lrc_params (dict): The dictionary returned by calculate_lrc_channel.
        index (int): The bar index (e.g., the most recent bar would be len(data) - 1).
        std_dev_multiplier (float): The number of std deviations to add/subtract.
                                    Use positive for upper bands, negative for lower bands.

    Returns:
        float: The calculated price level.
    """
    if not lrc_params:
        return 0.0

    base_price = lrc_params['slope'] * index + lrc_params['intercept']
    price_offset = std_dev_multiplier * lrc_params['std_dev']

    return base_price + price_offset 