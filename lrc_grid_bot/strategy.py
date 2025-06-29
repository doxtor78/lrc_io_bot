import numpy as np
from typing import Dict, List, Tuple

class Strategy:
    def __init__(self, config, lrc_calculator):
        self.config = config
        self.lrc_calculator = lrc_calculator

    def get_trade_direction_and_zones(self, lrc_params: dict) -> Tuple[str, dict]:
        """
        Determines the favored trade direction based on the LRC slope.
        
        Returns:
            A tuple containing the direction ('long' or 'short') and the favorable zones.
        """
        if lrc_params['slope'] > 0:
            return 'long', self.config.UPTREND_FAVORABLE_ZONES
        else:
            return 'short', self.config.DOWNTREND_FAVORABLE_ZONES

    def generate_entry_grid(self, lrc_params: dict, latest_index: int, direction: str, zones: dict) -> List[Dict[str, float]]:
        """
        Generates a grid of entry limit orders.

        Args:
            lrc_params: The calculated LRC parameters.
            latest_index: The index of the most recent candle.
            direction: The favored trade direction ('long' or 'short').
            zones: The dictionary of favorable zones for the current trend.

        Returns:
            A list of dictionaries, where each dict represents a suborder with 'price' and 'amount'.
        """
        if direction not in zones:
            return []

        zone_start_std, zone_end_std = zones[direction]
        
        # Create evenly spaced points within the standard deviation zone
        std_dev_points = np.linspace(zone_start_std, zone_end_std, self.config.SUB_ORDER_COUNT)
        
        grid_orders = []
        sub_order_size = self.config.MAIN_ORDER_SIZE_USD / self.config.SUB_ORDER_COUNT

        for std_dev in std_dev_points:
            price = self.lrc_calculator.get_price_at_index(lrc_params, latest_index, std_dev)
            grid_orders.append({'price': round(price, 2), 'amount': sub_order_size})
            
        return grid_orders

    def generate_tp_grid(self, lrc_params: dict, latest_index: int, position_side: str) -> List[Dict[str, float]]:
        """
        Generates a grid of take-profit limit orders.

        Args:
            lrc_params: The calculated LRC parameters.
            latest_index: The index of the most recent candle.
            position_side: The side of the current position ('long' or 'short').

        Returns:
            A list of dictionaries for the take-profit suborders.
        """
        if position_side == 'none' or position_side not in self.config.TAKE_PROFIT_ZONES:
            return []
            
        zone_start_std, zone_end_std = self.config.TAKE_PROFIT_ZONES[position_side]
        
        std_dev_points = np.linspace(zone_start_std, zone_end_std, self.config.SUB_ORDER_COUNT)
        
        grid_orders = []
        # For TP, the amount for each sub-order needs to be based on the actual position size
        # This will be handled in the main loop when we know the position size. Here we just calculate prices.
        
        for std_dev in std_dev_points:
            price = self.lrc_calculator.get_price_at_index(lrc_params, latest_index, std_dev)
            grid_orders.append({'price': round(price, 2)}) # Amount will be added later
            
        return grid_orders

    def get_stop_loss_prices(self, lrc_params: dict, latest_index: int, position_side: str) -> Dict[str, float]:
        """
        Calculates the price levels for the soft and hard stop losses.

        Args:
            lrc_params: The calculated LRC parameters.
            latest_index: The index of the most recent candle.
            position_side: The side of the current position ('long' or 'short').

        Returns:
            A dictionary with 'ssl_price' and 'hsl_price'.
        """
        if position_side == 'none':
            return {}

        # For a long position, stop losses are below. For a short, they are above.
        multiplier = -1 if position_side == 'long' else 1
        
        ssl_price = self.lrc_calculator.get_price_at_index(
            lrc_params, latest_index, self.config.SSL_LEVEL * multiplier
        )
        hsl_price = self.lrc_calculator.get_price_at_index(
            lrc_params, latest_index, self.config.HSL_LEVEL * multiplier
        )

        return {'ssl_price': round(ssl_price, 2), 'hsl_price': round(hsl_price, 2)} 