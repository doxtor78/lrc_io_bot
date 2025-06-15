# Bybit Testnet Trading Bot

This project implements a trading bot for testing strategies on Bybit's testnet platform.

## Setup Instructions

1. Create a testnet account:
   - Go to https://testnet.bybit.com/
   - Sign up for a testnet account
   - Get your API key and secret from the API Management section

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment:
   - Copy `.env.example` to `.env`
   - Fill in your API credentials and trading parameters

4. Run the bot:
   ```bash
   python main.py
   ```

## Features

- Connects to Bybit testnet
- Implements basic trading functionality
- Supports configurable trading parameters
- Includes error handling and logging

## Safety Notes

- This bot is designed for testnet use only
- Always test thoroughly on testnet before considering mainnet deployment
- Monitor the bot's performance and adjust parameters as needed

## Project Structure

- `main.py`: Main trading bot implementation
- `config.py`: Configuration and environment variable handling
- `requirements.txt`: Project dependencies
- `.env`: Environment variables (not tracked in git) 