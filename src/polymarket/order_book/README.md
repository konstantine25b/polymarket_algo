# Polymarket Order Book Analyzer

This module fetches and analyzes Polymarket order book data, focusing on Elon Musk tweet markets.

## Features

- Fetches real-time order book data from Polymarket's CLOB API
- Processes and organizes bid/ask orders
- Generates visualizations of order book depth
- Stores historical order book data
- Displays market status and probabilities in terminal
- Shows token IDs for easy market trading integration
- Returns market data in JSON format for programmatic use

## Usage

### Fetch Elon Musk Tweet Market Order Book

```bash
# Get current order book data for Elon Musk tweet markets
python -m src.polymarket.order_book.fetch_elon_market

# Fetch and visualize order book data
python -m src.polymarket.order_book.fetch_elon_market --visualize

# Fetch order book data and save to specific filename
python -m src.polymarket.order_book.fetch_elon_market --output elonmusk_orderbook_custom.json
```

### Generate Order Book Visualizations

```bash
# Generate visualizations from most recent order book data
python -m src.polymarket.order_book.visualize_order_book

# Generate visualizations from specific order book file
python -m src.polymarket.order_book.visualize_order_book --file data/elonmusk_orderbook_2023-05-15.json
```

### View Current Market Status

```bash
# Display current market percentages from most recent data
python -m src.polymarket.order_book.show_market_status

# Quick mode - compact output with essential market data
python -m src.polymarket.order_book.show_market_status --quick

# Quick refresh - fetch fresh data and show compact output
python -m src.polymarket.order_book.show_market_status --quick --refresh

# Show all available market data and additional statistics
python -m src.polymarket.order_book.show_market_status --all

# Include ASCII chart visualization in the terminal
python -m src.polymarket.order_book.show_market_status --visualize

# Fetch fresh data and display current market percentages
python -m src.polymarket.order_book.show_market_status --refresh

# Show token IDs for each market outcome
python -m src.polymarket.order_book.show_market_status --token-ids

# Quick view with token IDs for easy trading
python -m src.polymarket.order_book.show_market_status --quick --refresh --token-ids

# Continuously update market data every 5 minutes in quick mode
python -m src.polymarket.order_book.show_market_status --refresh --interval 300 --quick

# Full featured dashboard with all data, visualization, and auto-refresh
python -m src.polymarket.order_book.show_market_status --refresh --interval 60 --all --visualize

# Output market data in JSON format
python -m src.polymarket.order_book.show_market_status --json

# Output fresh market data in JSON format
python -m src.polymarket.order_book.show_market_status --refresh --json
```

### Using the JSON Output Programmatically

You can now directly access the market data in your Python code:

```python
from src.polymarket.order_book.show_market_status import get_market_data_json

# Get fresh market data
market_data = get_market_data_json(refresh=True)

# Access market probabilities
for range_name, details in market_data["markets"].items():
    print(f"{range_name}: {details['probability']}%")

# Access token IDs
for range_name, details in market_data["markets"].items():
    print(f"{range_name} token ID: {details['token_id']}")

# Get the expected value and most likely outcome
expected_value = market_data["summary"]["expected_value"]
most_likely = market_data["summary"]["most_likely"]["range"]
most_likely_prob = market_data["summary"]["most_likely"]["probability"]

print(f"Expected tweets: {expected_value}")
print(f"Most likely outcome: {most_likely} ({most_likely_prob}%)")
```

The market status display shows:

- Current probabilities for each tweet count range
- Best bid and ask prices
- Bid-ask spread
- Total market liquidity
- Most likely outcome
- Expected tweet count
- Data processing time

**Quick Mode** provides a compact display with essential market data:

- Clean, simple list of ranges with probabilities, bids, asks, spreads, and liquidity
- No logging or debug information
- Shortened range names (removes dates)
- Most likely outcome and expected tweet count
- Total market liquidity
- Data processing time in seconds
- Preserves terminal history on refresh (doesn't clear screen)

**All Data Mode** shows additional information:

- Separate bid and ask liquidity
- Total number of markets
- Total market liquidity
- Market with the tightest spread

**Visualization** adds an ASCII bar chart of the probabilities.

**Token IDs Mode** shows token IDs for each market outcome:

- Displays token IDs at the bottom of the market status output
- Use these IDs directly with the Polymarket trading API or the bidding module
- Ideal for automated trading strategies
- Combine with `--quick --refresh` flags for a streamlined trading view

**JSON Mode** returns structured data in JSON format:

- Returns all market data in a structured JSON format
- Includes probabilities, bids, asks, spreads, liquidity and token IDs
- Includes summary information (expected value, most likely outcome)
- Ideal for programmatic integration with other tools

## Data Format

The order book data is stored in JSON format with the following structure:

```json
{
  "timestamp": "2023-05-15T12:34:56Z",
  "event_title": "Elon Musk Tweet Count (May 15-22)",
  "questions": {
    "Will Elon tweet 100-124 times?": {
      "market_id": "0x123...",
      "token_id": "71321045679252212594626385532706912750332728571942532289631379312455583992563",
      "buy_orders": [
        {"price": 25.5, "size": 100.0, "total": 25.5},
        ...
      ],
      "sell_orders": [
        {"price": 28.2, "size": 50.0, "total": 14.1},
        ...
      ],
      "is_synthetic": false
    },
    ...
  }
}
```

## JSON Return Format

The `get_market_data_json()` function returns data in the following format:

```json
{
  "timestamp": "2023-05-15T12:34:56Z",
  "event_title": "Elon Musk Tweet Count (May 15-22)",
  "ranges": ["150–174", "175–199", "200–224"],
  "markets": {
    "150–174": {
      "probability": 87.0,
      "bid": 86.0,
      "ask": 88.0,
      "spread": 2.0,
      "bid_liquidity": 25000.0,
      "ask_liquidity": 25583.13,
      "liquidity": 50583.13,
      "token_id": "87484005561240668293386668024570478793193107613520178167348753968163790506784",
      "market_id": "0x123...",
      "original_question": "Will Elon tweet 150–174 times?"
    },
    ...
  },
  "summary": {
    "expected_value": 165.0,
    "total_liquidity": 128335.66,
    "most_likely": {
      "range": "150–174",
      "probability": 87.0
    }
  }
}
```

## Trading Integration

The order book module now includes token IDs for easy integration with Polymarket trading functionality. To trade directly based on market data:

1. Display market data with token IDs: `python -m src.polymarket.order_book.show_market_status --quick --refresh --token-ids`
2. Find the token ID for your desired market
3. Use the bidding module to place orders:

```python
from src.polymarket.bidding.buy.market_order import place_market_buy_order
from py_clob_client.clob_types import OrderType

# Place a market buy order using the token ID
response = place_market_buy_order(
    token_id="71321045679252212594626385532706912750332728571942532289631379312455583992563",
    amount_usd=10.0,
    order_type=OrderType.FOK
)
```

Alternatively, use the market buy CLI for command-line trading:

```bash
python -m src.scripts.market_buy.py --token-id 71321045679252212594626385532706912750332728571942532289631379312455583992563 --amount 10.0
```
