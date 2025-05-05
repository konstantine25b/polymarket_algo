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

# LARK Polymarket Algo

This repository contains algorithms and tools for analyzing and predicting Polymarket events, with a focus on Elon Musk's tweet patterns.

## Features

- Historical tweet data analysis tools
- Prediction algorithms for future tweet counts
- Polymarket event data fetching and visualization
- Order book analysis

## Modules

### Polymarket Module

For details on using the Polymarket module, see [src/polymarket/Readme.md](src/polymarket/Readme.md)

### Tweet Count Frame Probability Prediction

The repository includes a tool that combines the Polymarket count frames with tweet prediction models to generate probabilities for each frame. This is particularly useful for predicting which bracket of tweet counts is most likely for upcoming Polymarket events.

To use the tweet count frame probability predictor:

```bash
# Activate virtual environment
source venv/bin/activate

# Run with default settings (uses April 11-18, 2025 timeframe)
python -m src.polymarket_tweet_predictor

# Run with custom date range
python -m src.polymarket_tweet_predictor --start "2025-04-11 12:00:00" --end "2025-04-18 12:00:00"

# Use custom data file and disable trend adjustment
python -m src.polymarket_tweet_predictor --file /path/to/tweets.csv --no-trend

# Increase simulation accuracy
python -m src.polymarket_tweet_predictor --sims 5000
```

The output includes:

- The most likely tweet count frames with probabilities
- Detailed breakdowns across all possible frames
- Insight into the distribution of possible outcomes

### Elon Tweet Predictor

For details on using the Elon Tweet Predictor, see [src/algos/elon_tweet_predictor/README.md](src/algos/elon_tweet_predictor/README.md)

### Elon Musk Tweet Fetcher

The Elon Musk Tweet Fetcher allows you to fetch tweets from Elon Musk's Twitter account using the Apify Twitter scraper API.

#### Fetching Tweets

To fetch the latest tweets from Elon Musk and add them to the database:

```bash
# Activate virtual environment
source venv/bin/activate

# Fetch 40 tweets using the client method and add to database
python -m src.apify.get_elon_tweets --max-tweets 40 --use-client --add-to-db
```

#### Cost Information

- Fetching up to 40 tweets costs approximately 3.2 cents per request using the Apify API
- The `--use-client` flag ensures better reliability and faster processing
- For more details on the Tweet Fetcher, see [src/apify/README.md](src/apify/README.md)

#### Additional Options

```bash
# Get tweets since the latest one in the database
python -m src.apify.get_elon_tweets --max-tweets 40 --use-client --latest --add-to-db

# Debug mode (prints more details and doesn't save to database)
python -m src.apify.get_elon_tweets --max-tweets 40 --use-client --debug
```

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd polymarket_algo

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms of the MIT license.

## Automated Scheduler

This project includes an automated scheduler that can periodically fetch tweets and run predictions at configurable intervals.

### Running the Scheduler

```bash
# Activate virtual environment
source venv/bin/activate

# Run with default settings (every 20 minutes)
python -m src.scheduler

# Run with custom interval (every 5 minutes)
python -m src.scheduler --interval 5

# Only fetch tweets, don't run predictions
python -m src.scheduler --tweets-only

# Only run predictions, don't fetch tweets
python -m src.scheduler --predictions-only

# Run jobs once and exit (don't keep running)
python -m src.scheduler --run-once
```

### Running as a Background Service

Use the provided shell scripts to run the scheduler as a background service:

```bash
# Start the scheduler with default settings
./src/scheduler/run_scheduler.sh

# Start with custom settings
./src/scheduler/run_scheduler.sh --interval 15 --max-tweets 50 --quiet

# Stop the scheduler
./src/scheduler/stop_scheduler.sh
```

For more details, see the [Scheduler README](src/scheduler/README.md).

# Polymarket Algorithmic Trading and Analysis

A Python library for interacting with the Polymarket CLOB API, analyzing trade data, and generating advanced visualizations.

## Features

- **API Client**: Wrapper for the Polymarket CLOB API
- **Trade Analysis**: Analyze price movements, volumes, and trading patterns
- **Advanced Visualizations**: Create beautiful, informative visualizations of trade data
- **Market Monitoring**: Tools for monitoring market conditions
- **Various Usage Examples**: Ready-to-use examples showing how to interact with the API

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/polymarket_algo.git
cd polymarket_algo
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your Polymarket API credentials:
```
WALLET_PRIVATE_KEY=your_private_key_here
```

## Usage

### Basic API Interaction

```python
from src.polymarket.client import PolymarketClient

# Initialize client
client = PolymarketClient()

# Get market details
market_id = '0x1234...'
market = client.get_market(market_id)
print(market)

# Get trades
trades = client.get_trades(market_id, limit=50)
print(f"Retrieved {len(trades)} trades")
```

### Trade Analysis and Visualization

This library provides powerful tools for analyzing Polymarket trade data and generating beautiful visualizations.

#### Quick Start

Use the provided `run.py` script for quick analysis and visualization:

```bash
# Run full analysis and create visualizations
python run.py --input path/to/your/trades.json --market "Market Name" --output results_dir

# Generate only visualizations
python run.py --input path/to/your/trades.json --market "Market Name" --output results_dir --viz-only
```

#### Using the Visualizer in Your Code

The enhanced visualizer can be used directly in your code:

```python
import pandas as pd
from src.polymarket.trade_analysis.visualizer import PolymarketTradeVisualizer

# Prepare your trade data as a pandas DataFrame
df = pd.DataFrame(trades)

# Initialize the visualizer
visualizer = PolymarketTradeVisualizer(
    theme='dark_background',  # Use 'darkgrid' for light theme
    output_dir='my_visualizations',
    dpi=300  # High resolution for output images
)

# Create price history chart
visualizer.plot_price_history(
    df=df,
    market_name="My Market",
    save_file=True
)

# Create volume distribution by outcome
visualizer.plot_volume_distribution(
    df=df,
    by='outcome',
    save_file=True
)

# Create price distribution analysis
visualizer.plot_price_distribution(
    df=df,
    save_file=True
)

# Create trading activity heatmap
visualizer.plot_trade_heatmap(
    df=df,
    save_file=True
)

# Create comprehensive dashboard
visualizer.create_dashboard(
    df=df,
    market_name="My Market",
    save_file=True
)
```

#### Using the Trade Analyzer

For comprehensive trade analysis:

```python
from src.polymarket.trade_analysis.trade_analyzer import PolymarketTradeAnalyzer

# Initialize analyzer
analyzer = PolymarketTradeAnalyzer(output_dir='analysis_results')

# Run complete analysis
results = analyzer.analyze_all(
    trades=trades,
    market_name="My Market",
    create_visualizations=True
)

# Print price analysis summary
print(results['price']['summary'])

# Print volume analysis summary
print(results['volume']['summary'])

# Print trading pattern analysis summary
print(results['patterns']['summary'])
```

## Available Visualizations

The enhanced visualizer produces several types of beautiful data visualizations:

1. **Price History Chart**: Shows price evolution over time with volume bars
2. **Volume Distribution**: Analyzes trading volume by outcome or side
3. **Price Distribution**: Histogram and boxplot analysis of price distribution
4. **Trading Heatmap**: Shows activity patterns by day and hour
5. **Comprehensive Dashboard**: Combined visualization with all key charts

All visualizations include summary statistics and are saved as high-quality PNG files.

## Examples

Explore the `examples/` directory for more usage examples:

- `examples/basic_example.py`: Basic API interaction
- `examples/visualizer_example.py`: Generate sample visualizations
- `examples/trade_analysis_example.py`: Perform trade analysis

To run any example:
```bash
python examples/visualizer_example.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
