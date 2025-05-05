# Polymarket Bidding Module

This module provides functionality for interacting with the Polymarket CLOB API, including creating and executing market buy and sell orders.

## Setup

1. Make sure you have the required dependencies installed:

   ```
   pip install py-clob-client python-dotenv
   ```

2. Set up your environment variables in a `.env` file:

   ```
   WALLET_PRIVATE_KEY=your_private_key_here
   ```

   **Important**: Your private key should be kept secure and never committed to version control.

## Usage

### Basic Client Usage

```python
from src.polymarket.bidding import PolymarketClient

# Initialize client
client = PolymarketClient()  # Will load private key from .env file

# Or provide private key directly
# client = PolymarketClient(private_key="your_private_key_here")

# Get wallet address
address = client.get_wallet_address()
print(f"Connected with wallet: {address}")

# Get trades
trades = client.get_trades()
print(trades)
```

### Executing Market Buy Orders

```python
from src.polymarket.bidding import PolymarketClient, MarketBuyOrder

# Initialize client
client = PolymarketClient()

# Create market buy order handler
market_buy = MarketBuyOrder(client)

# Execute a market buy order
token_id = "93124055671959869958037846065354081314545895099992000276527130498502400601286"
amount = 1

response = market_buy.execute_order(token_id, amount)
print(response)
```

### Executing Market Sell Orders

```python
from src.polymarket.bidding import PolymarketClient, MarketSellOrder

# Initialize client
client = PolymarketClient()

# Create market sell order handler
market_sell = MarketSellOrder(client)

# Execute a market sell order
token_id = "93124055671959869958037846065354081314545895099992000276527130498502400601286"
amount = 1

response = market_sell.execute_order(token_id, amount)
print(response)
```

## Running from Command Line

### Market Buy Orders

The module includes a Python script to execute market buy orders directly from the command line:

```bash
# Run the script with token_id and amount
python -m src.polymarket.bidding.buy.market.run 93124055671959869958037846065354081314545895099992000276527130498502400601286 1
```

Where:

- First argument is the token_id of the market you want to buy
- Second argument is the amount you want to buy

You can also import and use the run function in your own scripts:

```python
from src.polymarket.bidding.buy.market import run_market_buy

# Execute a market buy order
token_id = "93124055671959869958037846065354081314545895099992000276527130498502400601286"
amount = 1

response = run_market_buy(token_id, amount)
print(response)
```

### Market Sell Orders

Similarly, you can execute market sell orders from the command line:

```bash
# Run the script with token_id and amount
python -m src.polymarket.bidding.sell.market.run 93124055671959869958037846065354081314545895099992000276527130498502400601286 1
```

Where:

- First argument is the token_id of the market you want to sell
- Second argument is the amount you want to sell

You can also import and use the run function in your own scripts:

```python
from src.polymarket.bidding.sell.market import run_market_sell

# Execute a market sell order
token_id = "93124055671959869958037846065354081314545895099992000276527130498502400601286"
amount = 1

response = run_market_sell(token_id, amount)
print(response)
```
