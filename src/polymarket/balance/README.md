# Polymarket Wallet Balance Checker

This module provides functionality to check wallet balances on the Polygon network where Polymarket operates. It can retrieve both MATIC (native token) and USDC balances for a specified wallet address.

## Features

- **Balance Checking**: Check MATIC and USDC token balances for a wallet on Polygon
- **Multiple Data Sources**: Attempts to get data from both Polymarket CLOB API and Polygon RPC
- **Environment Integration**: Automatically uses wallet address from `.env` file
- **Command-line Interface**: Easily check balances from the terminal

## Requirements

- Python 3.8+
- `web3` library
- `py_clob_client` library
- `python-dotenv` for environment variable management

## Setup

Make sure your `.env` file contains:

```
WALLET_ADDRESS=0x7954E7cD33604505fe71a925f452871436790B85
WALLET_PRIVATE_KEY=your_private_key_here
```

## Usage

### Python API

```python
from src.polymarket.balance import check_wallet_balance

# Check balance using wallet address from .env
balance_info = check_wallet_balance()
print(f"MATIC Balance: {balance_info['matic_balance']}")
print(f"USDC Balance: {balance_info['usdc_balance']}")

# Check balance for a specific address
balance_info = check_wallet_balance("0x7954E7cD33604505fe71a925f452871436790B85")
```

### Command-line Usage

For a simple check of your wallet balance (using the address in `.env`):

```bash
# Use the wallet.py script directly
python -m src.polymarket.balance.wallet

# Use the CLI tool with more options
python -m src.polymarket.balance.balance_cli

# Check a different wallet address
python -m src.polymarket.balance.balance_cli --wallet 0xYourWalletAddress

# Get JSON output
python -m src.polymarket.balance.balance_cli --json
```

## How It Works

1. The module first attempts to use the Polymarket CLOB API to get USDC balance
2. It also queries the Polygon RPC to get native MATIC balance
3. If the CLOB API fails, it falls back to using the Polygon RPC for USDC balance using the token contract

## Return Format

The `check_wallet_balance` function returns a dictionary with the following structure:

```python
{
    "wallet": "0x7954E7cD33604505fe71a925f452871436790B85",
    "matic_balance": 1.234,  # MATIC balance as float
    "usdc_balance": 100.0,   # USDC balance as float
    "success": True,         # Whether any balance retrieval was successful
    "error": None            # Error message if any
}
```
