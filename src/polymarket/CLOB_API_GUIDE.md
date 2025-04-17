# Polymarket CLOB API Guide

This guide explains how to interact with Polymarket's Central Limit Order Book (CLOB) API using the utilities provided in the Polymarket Data Analyzer.

## Overview

The CLOB API provides access to Polymarket's order book data, allowing you to:

1. Get information about available markets
2. Fetch order books for specific markets
3. Get price information (bids, asks, midpoints, spreads)
4. Analyze market liquidity and reward opportunities

## Getting Started

### Basic Imports

```python
from src.polymarket.clob_utils import ClobUtils
from py_clob_client.clob_types import BookParams

# Initialize the CLOB utils
clob = ClobUtils()
```

### Key Concepts

- **Token ID**: Each outcome (YES/NO) in a Polymarket market has a unique token ID
- **Condition ID**: Unique identifier for a market
- **Order Book**: Collection of buy (bid) and sell (ask) orders for a specific token
- **Midpoint**: Average of the best bid and best ask prices
- **Spread**: Difference between the best ask and best bid prices

## Market Discovery

### Getting All Markets

```python
# Fetch all available markets
markets = clob.fetch_all_markets()

# Print total number of markets
print(f"Found {len(markets)} markets")

# Print details of the first market
first_market = markets[0]
print(f"Market ID: {first_market.get('condition_id')}")
print(f"Tokens: {first_market.get('tokens')}")
```

### Finding Markets with Rewards

```python
# Fetch markets with rewards enabled
rewarded_markets = clob.fetch_all_rewarded_markets()

for market in rewarded_markets[:5]:  # Show first 5
    condition_id = market.get("condition_id", "")
    rewards = market.get("rewards", {})
    min_size = rewards.get("min_size", 0)
    max_spread = rewards.get("max_spread", 0)

    print(f"Market ID: {condition_id}")
    print(f"Min Size: {min_size}, Max Spread: {max_spread}")
```

### Get Details for a Specific Market

```python
# Get details for a specific market by condition ID
condition_id = "0x1234..."  # Replace with actual condition ID
market = clob.get_market(condition_id=condition_id)

# Extract YES and NO tokens
tokens = market.get("tokens", [])
yes_token = next((t for t in tokens if t.get("outcome", "").upper() == "YES"), None)
no_token = next((t for t in tokens if t.get("outcome", "").upper() == "NO"), None)

if yes_token and no_token:
    yes_token_id = yes_token.get("token_id", "")
    no_token_id = no_token.get("token_id", "")
    print(f"YES Token ID: {yes_token_id}")
    print(f"NO Token ID: {no_token_id}")
```

## Order Book Data

### Get Order Book for a Token

```python
# Get order book for a specific token
token_id = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
order_book = clob.get_order_book(token_id)

# Format into a standardized structure
formatted = clob.format_order_book(order_book)

# Print top buy and sell orders
buy_orders = formatted.get("buy_orders", [])
sell_orders = formatted.get("sell_orders", [])

print("Top 3 Buy Orders:")
for order in buy_orders[:3]:
    print(f"Price: {order.get('price', 0):.2f}%, Size: {order.get('size', 0):.2f}")

print("\nTop 3 Sell Orders:")
for order in sell_orders[:3]:
    print(f"Price: {order.get('price', 0):.2f}%, Size: {order.get('size', 0):.2f}")
```

### Get Multiple Order Books at Once

```python
# Get order books for multiple tokens
token_ids = [
    "71321045679252212594626385532706912750332728571942532289631379312455583992563",
    "52114319501245915516055106046884209969926127482827954674443846427813813222426"
]
order_books = clob.get_order_books(token_ids)

# Process each order book
for book in order_books:
    asset_id = book.get("asset_id", "")
    bids = book.get("bids", [])
    asks = book.get("asks", [])

    print(f"Token ID: {asset_id}")
    print(f"Bids: {len(bids)}, Asks: {len(asks)}")
```

## Prices and Spreads

### Get Midpoint

```python
# Get the midpoint price for a token
token_id = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
midpoint = clob.get_midpoint(token_id)

print(f"Midpoint: {midpoint:.4f} ({midpoint*100:.2f}%)")
```

### Get Midpoints for Multiple Tokens

```python
# Get midpoints for multiple tokens
token_ids = [
    "71321045679252212594626385532706912750332728571942532289631379312455583992563",
    "52114319501245915516055106046884209969926127482827954674443846427813813222426"
]
midpoints = clob.get_midpoints(token_ids)

for token_id, midpoint in midpoints.items():
    print(f"Token ID: {token_id}, Midpoint: {midpoint:.4f} ({midpoint*100:.2f}%)")
```

### Get Buy/Sell Prices

```python
# Get the best buy (bid) price for a token
token_id = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
buy_price = clob.get_price(token_id, side="buy")

# Get the best sell (ask) price for a token
sell_price = clob.get_price(token_id, side="sell")

print(f"Best Bid: {buy_price:.4f} ({buy_price*100:.2f}%)")
print(f"Best Ask: {sell_price:.4f} ({sell_price*100:.2f}%)")
```

### Get Multiple Prices

```python
# Get prices for multiple tokens and sides
token_ids = [
    "71321045679252212594626385532706912750332728571942532289631379312455583992563",
    "71321045679252212594626385532706912750332728571942532289631379312455583992563"
]
sides = ["BUY", "SELL"]

prices = clob.get_prices(token_ids, sides)

for token_id, side_prices in prices.items():
    buy_price = side_prices.get("BUY", 0)
    sell_price = side_prices.get("SELL", 0)

    print(f"Token ID: {token_id}")
    print(f"Buy: {buy_price:.4f}, Sell: {sell_price:.4f}")
```

### Get Spread

```python
# Get the spread for a token
token_id = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
spread = clob.get_spread(token_id)

print(f"Spread Data: {spread}")
```

## Liquidity Analysis

### Calculate Liquidity Metrics

```python
# Get order book for a token
token_id = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
order_book = clob.get_order_book(token_id)
formatted = clob.format_order_book(order_book)

# Calculate liquidity metrics
buy_orders = formatted.get("buy_orders", [])
sell_orders = formatted.get("sell_orders", [])

buy_liquidity = sum(order.get("total", 0) for order in buy_orders)
sell_liquidity = sum(order.get("total", 0) for order in sell_orders)
total_liquidity = buy_liquidity + sell_liquidity

best_bid = max([order.get("price", 0) for order in buy_orders]) if buy_orders else 0
best_ask = min([order.get("price", 0) for order in sell_orders]) if sell_orders else 100

spread = best_ask - best_bid if best_bid > 0 and best_ask < 100 else None
spread_pct = (spread / best_bid * 100) if spread is not None and best_bid > 0 else None

print(f"Buy Liquidity: ${buy_liquidity:.2f}")
print(f"Sell Liquidity: ${sell_liquidity:.2f}")
print(f"Total Liquidity: ${total_liquidity:.2f}")
print(f"Best Bid: {best_bid:.2f}%, Best Ask: {best_ask:.2f}%")
if spread is not None:
    print(f"Spread: {spread:.2f}% ({spread_pct:.2f}%)")
```

## Advanced Functionality

### Paginated API Requests

The CLOB API uses cursor-based pagination. When fetching large amounts of data, you'll need to handle pagination:

```python
# Fetch all simplified markets with pagination
all_markets = []
next_cursor = ""

while True:
    response = clob.get_simplified_markets(next_cursor)
    markets = response.get("data", [])
    all_markets.extend(markets)

    # Check if we've reached the end
    next_cursor = response.get("next_cursor", "LTE=")
    if next_cursor == "LTE=" or not markets:
        break

print(f"Total markets fetched: {len(all_markets)}")
```

### Extract Tokens from Markets

```python
# Extract token pairs from a list of markets
markets = clob.fetch_all_markets()
tokens = clob.extract_tokens_from_markets(markets)

print(f"Extracted {len(tokens)} token pairs")
```

## Full Example: Market Analysis

Here's a complete example that analyzes a market for trading opportunities:

```python
from src.polymarket.clob_utils import ClobUtils

def analyze_trading_opportunity(condition_id):
    # Initialize CLOB utils
    clob = ClobUtils()

    # Get market details
    market = clob.get_market(condition_id=condition_id)

    # Extract tokens
    tokens = market.get("tokens", [])
    yes_token = next((t for t in tokens if t.get("outcome", "").upper() == "YES"), None)
    no_token = next((t for t in tokens if t.get("outcome", "").upper() == "NO"), None)

    if not yes_token or not no_token:
        return "Could not identify YES and NO tokens"

    yes_token_id = yes_token.get("token_id", "")
    no_token_id = no_token.get("token_id", "")

    # Get midpoints
    yes_midpoint = clob.get_midpoint(yes_token_id)
    no_midpoint = clob.get_midpoint(no_token_id)

    # Check for arbitrage opportunity
    market_sum = yes_midpoint + no_midpoint

    if market_sum < 0.99:
        opportunity = f"Potential long arbitrage: YES + NO = {market_sum:.4f}, profit = {(1-market_sum)*100:.2f}%"
    elif market_sum > 1.01:
        opportunity = f"Potential short arbitrage: YES + NO = {market_sum:.4f}, profit = {(market_sum-1)*100:.2f}%"
    else:
        opportunity = f"No clear arbitrage: YES + NO = {market_sum:.4f}"

    # Get order books
    yes_order_book = clob.get_order_book(yes_token_id)
    no_order_book = clob.get_order_book(no_token_id)

    # Format order books
    yes_formatted = clob.format_order_book(yes_order_book)
    no_formatted = clob.format_order_book(no_order_book)

    # Check for liquidity
    yes_buy_liquidity = sum(order.get("total", 0) for order in yes_formatted.get("buy_orders", []))
    yes_sell_liquidity = sum(order.get("total", 0) for order in yes_formatted.get("sell_orders", []))

    no_buy_liquidity = sum(order.get("total", 0) for order in no_formatted.get("buy_orders", []))
    no_sell_liquidity = sum(order.get("total", 0) for order in no_formatted.get("sell_orders", []))

    # Return analysis
    return {
        "market_name": market.get("market", {}).get("question", "Unknown"),
        "opportunity": opportunity,
        "yes_midpoint": yes_midpoint,
        "no_midpoint": no_midpoint,
        "market_sum": market_sum,
        "yes_liquidity": yes_buy_liquidity + yes_sell_liquidity,
        "no_liquidity": no_buy_liquidity + no_sell_liquidity,
        "total_liquidity": yes_buy_liquidity + yes_sell_liquidity + no_buy_liquidity + no_sell_liquidity
    }

# Example usage
result = analyze_trading_opportunity("0x1234...")  # Replace with an actual condition ID
print(result)
```

## Using the Market Scanner

The `market_scanner.py` script provides a ready-to-use command-line interface for scanning and analyzing Polymarket markets:

```bash
# Scan for markets with rewards
python -m src.polymarket.market_scanner --rewarded --verbose

# Find the most liquid markets
python -m src.polymarket.market_scanner --liquid --top 20

# Analyze a specific market by condition ID
python -m src.polymarket.market_scanner --market "0x1234..." --save

# Combining options
python -m src.polymarket.market_scanner --liquid --rewarded --verbose
```

## Troubleshooting

1. **Missing Token ID**: If you get errors about missing token IDs, check that you're using the correct condition ID and that the market exists.

2. **Empty Order Book**: Some tokens may have limited liquidity and return empty order books. This is normal for less active markets.

3. **Rate Limiting**: If you're making many requests in a short period, you might experience rate limiting. Add delays between requests if needed.

4. **Invalid Pagination Cursor**: If you're getting errors when using pagination, ensure you're handling the cursor correctly. An empty string means start from the beginning, and "LTE=" means you've reached the end.

## API Reference

- `get_sampling_markets(next_cursor)`: Get markets with rewards
- `get_simplified_markets(next_cursor)`: Get markets in a reduced schema
- `get_sampling_simplified_markets(next_cursor)`: Get markets with rewards in a reduced schema
- `get_market(condition_id)`: Get a single market
- `get_order_book(token_id)`: Get order book for a token
- `get_order_books(token_ids)`: Get order books for multiple tokens
- `get_price(token_id, side)`: Get price for a token (side = "buy" or "sell")
- `get_prices(token_ids, sides)`: Get prices for multiple tokens and sides
- `get_midpoint(token_id)`: Get midpoint for a token
- `get_midpoints(token_ids)`: Get midpoints for multiple tokens
- `get_spread(token_id)`: Get spread for a token
