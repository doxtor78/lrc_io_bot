import json
import os
from typing import Dict, Any

# Define a default state structure
DEFAULT_STATE = {
    "position": {
        "side": "none",  # 'long', 'short', or 'none'
        "size_contracts": 0.0,
        "entry_price": 0.0
    },
    "active_orders": {
        "entry": [],  # List of entry order dicts
        "tp": [],     # List of take-profit order dicts
        "ssl": {},    # The Soft Stop Loss order dict
        "hsl": {}     # The Hard Stop Loss order dict
    },
    "ssl_trigger": {
        "is_active": False,
        "first_breach_timestamp": 0
    }
}

class StateManager:
    def __init__(self, state_file_path: str, logger):
        self.state_file_path = state_file_path
        self.logger = logger
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads the state from the JSON file, or returns a default state if not found."""
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, 'r') as f:
                    self.logger.info(f"Loading existing state from {self.state_file_path}")
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error loading state file: {e}. Starting with a fresh state.")
                return DEFAULT_STATE
        else:
            self.logger.info("No state file found. Starting with a fresh state.")
            return DEFAULT_STATE

    def save_state(self):
        """Saves the current state to the JSON file."""
        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(self.state, f, indent=4)
            self.logger.debug("Successfully saved state.")
        except IOError as e:
            self.logger.error(f"Could not save state to {self.state_file_path}: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Returns the current state."""
        return self.state

    def update_state(self, key: str, value: Any):
        """Updates a top-level key in the state and saves it."""
        if key in self.state:
            self.state[key] = value
            self.save_state()
        else:
            self.logger.warning(f"Attempted to update a non-existent key '{key}' in state.")

    def reset_state(self):
        """Resets the state to its default and saves it."""
        self.logger.info("Resetting bot state to default.")
        self.state = DEFAULT_STATE
        self.save_state() 