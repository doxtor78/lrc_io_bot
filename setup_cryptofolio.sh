#!/bin/bash

# Create project directory
mkdir -p cryptofolio_project
cd cryptofolio_project

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Clone Cryptofolio repository
git clone https://github.com/Xtrendence/Cryptofolio.git

# Change to Cryptofolio directory
cd Cryptofolio

# Install dependencies (we'll add these as we identify them)
pip install -r requirements.txt

echo "Setup complete! You are now in the Cryptofolio project directory with an activated virtual environment." 