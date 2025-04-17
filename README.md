# Polymarket Algorithmic Analysis

A collection of algorithms and tools for analyzing Elon Musk's tweeting patterns and related markets.

## Setup

```bash
# Set up virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Available Modules

### 1. Data Formatting

Prepares tweet data for analysis:

```bash
# Format raw tweet data
python3 src/formating_tweet_data/fixDates.py

# Aggregate tweets by day
python3 src/formating_tweet_data/formatByDay.py
```

### 2. Prediction Algorithms

Various algorithms for predicting Elon Musk's tweeting patterns:

See `src/algos/README.md` for details on available prediction algorithms.

### 3. Polymarket Analysis

Tools for analyzing Polymarket data related to Elon Musk's tweeting:

```bash
# Get current timeframes and odds from Polymarket
python3 -m src.polymarket.main

# Generate visualization plots
python3 -m src.polymarket.main --generate-plot

# Fetch and display order book data
python3 -m src.polymarket.main --order-frames
```

#### Polymarket Data Analyzer CLI Options

```
--url URL             URL of the Polymarket event
--save-data           Save data to JSON and CSV files
--generate-plot       Generate visualization plots for market probabilities
--order-frames        Fetch and display order book frames
--detailed-orders     Show detailed buy and sell orders (requires --order-frames)
--save-orders         Save order book data to JSON (requires --order-frames)
--visualize-orders    Generate visualizations of order books (requires --order-frames)
--compare             Compare with previous data (requires --save-data)
--list-events         List all previously stored events
```

Example with custom URL:

```bash
python3 -m src.polymarket.main --url "https://polymarket.com/event/your-event-slug" --generate-plot
```

### 4. Order Book Analysis and CLOB API

Advanced utilities for working with Polymarket's Central Limit Order Book (CLOB) API:

```bash
# Scan for markets with rewards
python3 -m src.polymarket.market_scanner --rewarded --verbose

# Find the most liquid markets
python3 -m src.polymarket.market_scanner --liquid --top 20

# Analyze a specific market by condition ID
python3 -m src.polymarket.market_scanner --market "your-condition-id" --save
```

#### Market Scanner CLI Options

```
--rewarded       Scan for markets with rewards
--liquid         Find most liquid markets
--market ID      Analyze a specific market by condition ID
--top N          Number of top markets to return (default: 10)
--verbose        Print detailed information
--save           Save analysis results to a file
```

For detailed information on using the CLOB API, see `src/polymarket/CLOB_API_GUIDE.md`.

### 5. Order Book Analysis Library

The `OrderBookAnalyzer` class provides comprehensive analysis of Polymarket order books:

```bash
# Run the analyzer on a specific event
python3 -m src.polymarket.order_book_analysis --slug "your-event-slug" --visualize
```

Features include:

- Liquidity metrics calculation
- Price manipulation detection
- Order book depth visualization
- Historical comparison
- Market anomaly detection

## Output

Results from the Polymarket analysis are saved in:

- Market data: `src/polymarket/data/{json|csv}`
- Order book data: `src/polymarket/data/order_books`
- Visualizations: `src/polymarket/plots`
- Market analysis: `src/polymarket/data/analysis`

## Advanced API Usage

The project includes comprehensive utilities for working with Polymarket's APIs:

1. **Main API Client**: `PolymarketAPIClient` class for fetching market data
2. **CLOB Utilities**: `ClobUtils` class for working with the CLOB API
3. **Order Book Analysis**: `OrderBookAnalyzer` class for analyzing order books
4. **Market Scanner**: Command-line utility for scanning markets

For programmatic access to the CLOB API:

```python
from src.polymarket.clob_utils import ClobUtils

# Initialize the client
clob = ClobUtils()

# Get all markets with rewards
rewarded_markets = clob.fetch_all_rewarded_markets()

# Get order book for a specific token
token_id = "your-token-id"
order_book = clob.get_order_book(token_id)
formatted = clob.format_order_book(order_book)

# Print the bid-ask spread
best_bid = max([o.get("price", 0) for o in formatted.get("buy_orders", [])]) if formatted.get("buy_orders") else 0
best_ask = min([o.get("price", 0) for o in formatted.get("sell_orders", [])]) if formatted.get("sell_orders") else 100
spread = best_ask - best_bid if best_bid > 0 and best_ask < 100 else 0
print(f"Spread: {spread:.2f}%")
```
