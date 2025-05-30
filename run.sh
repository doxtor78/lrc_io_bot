#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Verify we're in the virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Error: Virtual environment not activated!"
    exit 1
fi

# Run the Python script
python funding_rates.py 