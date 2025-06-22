#!/bin/bash

# Activate virtual environment
source ../../venv/bin/activate

# Verify we're in the virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Error: Virtual environment not activated!"
    exit 1
fi

# Set Kraken API credentials
export KRAKEN_API_KEY='t3n4lPWHORPVuvIN8Fcr92TFTLy5UmLIXqQhvZaGNQGlmRy8IHf3vHNx'
export KRAKEN_API_SECRET='1Vr8rpYuhnSGAIpOltsDSraPnr3J3nPHDNidEEKonbzwON+chMKZO9w2cHLhLJMlpd1M7UosydlPGlajM3kp1g=='

# Run the Python script
python funding_rates.py 