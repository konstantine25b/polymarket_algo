# Polymarket Order Book Analyzer

This module fetches and analyzes Polymarket order book data, focusing on Elon Musk tweet markets.

## Features

- Fetches real-time order book data from Polymarket's CLOB API
- Processes and organizes bid/ask orders
- Generates visualizations of order book depth
- Stores historical order book data
- Displays market status and probabilities in terminal

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

# Continuously update market data every 5 minutes in quick mode
python -m src.polymarket.order_book.show_market_status --refresh --interval 300 --quick

# Full featured dashboard with all data, visualization, and auto-refresh
python -m src.polymarket.order_book.show_market_status --refresh --interval 60 --all --visualize
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

## Data Format

The order book data is stored in JSON format with the following structure:

```json
{
  "timestamp": "2023-05-15T12:34:56Z",
  "event_title": "Elon Musk Tweet Count (May 15-22)",
  "questions": {
    "Will Elon tweet 100-124 times?": {
      "market_id": "0x123...",
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
