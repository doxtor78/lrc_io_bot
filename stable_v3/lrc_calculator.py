import numpy as np

def calculate_lrc_parameters(data, use_date_range=False, start_timestamp=None):
    """
    Calculates the key parameters of a Linear Regression Channel, ensuring
    the result can be drawn as a perfectly straight line.

    This version regresses against the BAR INDEX to match TradingView's method.

    Args:
        data (list of dicts): A list of candlestick data points.
        use_date_range (bool): If True, calculation starts from start_timestamp.
        start_timestamp (int): The Unix timestamp to start the calculation from.

    Returns:
        dict: A dictionary containing the slope, intercept, standard deviation,
              and start/end points of the channel.
    """
    if not data:
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

    # --- 4. Return the essential parameters, not the wobbly point-by-point line ---
    start_point_index = 0
    end_point_index = len(indices) - 1

    start_price = slope * start_point_index + intercept
    end_price = slope * end_point_index + intercept
    
    start_time = calc_data[start_point_index]['time']
    end_time = calc_data[end_point_index]['time']

    # --- 5. Calculate channel lines based on the single regression ---
    # The standard deviation is a fixed vertical offset from the main line.
    
    # Mid Line
    mid_line_start = {'time': start_time, 'price': start_price}
    mid_line_end = {'time': end_time, 'price': end_price}

    # Upper Channel (1 Std Dev)
    upper_channel_start = {'time': start_time, 'price': start_price + std_dev}
    upper_channel_end = {'time': end_time, 'price': end_price + std_dev}

    # Lower Channel (1 Std Dev)
    lower_channel_start = {'time': start_time, 'price': start_price - std_dev}
    lower_channel_end = {'time': end_time, 'price': end_price - std_dev}

    return {
        'start_time': calc_data[start_point_index]['time'],
        'start_price': start_price,
        'end_time': calc_data[end_point_index]['time'],
        'end_price': end_price,
        'std_dev': std_dev,
        'slope': slope,
        'intercept': intercept
    } 