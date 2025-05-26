# Polymarket Trade Analysis

A set of Python tools for analyzing and visualizing Polymarket trade data retrieved from the Polymarket CLOB (Central Limit Order Book) API.

## Quick Start

```bash
# From the main project directory:
python -m src.polymarket.trade_analysis.run

# OR navigate to the trade_analysis directory:
cd src/polymarket/trade_analysis
python run.py
```

## How to Run

### Option 1: From the Main Project Directory (Recommended)

You can run the analysis directly from your project's root directory:

```bash
# Install requirements first
pip install -r src/polymarket/trade_analysis/requirements.txt

# Create a .env file in the project root with your wallet private key
echo "WALLET_PRIVATE_KEY=0x123abc..." > .env  # Replace with your actual key

# Run the analysis
python -m src.polymarket.trade_analysis.run
```

### Option 2: From the Trade Analysis Directory

If you prefer, you can navigate to the trade_analysis directory and run from there:

```bash
# Navigate to the directory
cd src/polymarket/trade_analysis

# Install requirements
pip install -r requirements.txt

# Create a .env file with your wallet private key
echo "WALLET_PRIVATE_KEY=0x123abc..." > .env  # Replace with your actual key

# Run the analysis
python run.py
```

## Setup Details

### Step 1: Installation

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install -r src/polymarket/trade_analysis/requirements.txt
```

### Step 2: Setup Authentication

Create a `.env` file with your Polymarket wallet private key:

```
WALLET_PRIVATE_KEY=0x123abc...  # Your actual private key here
```

_Note: You can place the .env file in either the project root or in the trade_analysis directory._

### Step 3: Run the Analysis

The analysis script provides:

- Error handling and user feedback
- A dedicated plots directory for the visualizations
- Option to look for trades where you're a taker if no maker trades are found
- Troubleshooting tips if something goes wrong

#### Running with the standalone runner script

```bash
# From project root
python -m src.polymarket.trade_analysis.run

# OR from the trade_analysis directory
python run.py
```

#### Running the example script

You can also use the example script:

```bash
# From project root
python -m src.polymarket.trade_analysis.example
```

### Step 4: View Results

- Analysis results will be displayed in the console
- Visualization files (PNG) will be created in the `plots` subdirectory
- Open the PNG files in any image viewer to see the visualizations

## Generated Visualizations

The package creates several visualizations:

1. **Price History**: Shows how prices changed over time
2. **Volume Distribution**: Shows trading volume by outcome
3. **Price Distribution**: Histogram of trade prices
4. **Trading Activity Heatmap**: Shows trading activity patterns by time
5. **Trade Dashboard**: Comprehensive dashboard combining multiple charts

All visualizations are saved as high-quality PNG files that can be:

- Viewed in any image viewer
- Included in reports or presentations
- Shared easily without requiring special software

## Overview

This package provides two main classes:

1. **PolymarketTradeAnalyzer**: For retrieving and analyzing trade data
2. **PolymarketTradeVisualizer**: For creating visualizations of trade data

## Trade Data Structure

The Polymarket API returns trade data in the following format:

```json
{
  "id": "203e535f-bd76-4610-8fd8-33e6e10e63a2",
  "taker_order_id": "0xad2b752f1d000fb17c825a38dd2c4be24af539e029a22776af53f932d44fe263",
  "market": "0x7bedaca7d17a565de42bbf4c0e25535396350bc6026adf1e6c633e3d42aadf63",
  "asset_id": "93124055671959869958037846065354081314545895099992000276527130498502400601286",
  "side": "BUY",
  "size": "4",
  "fee_rate_bps": "0",
  "price": "0.25",
  "status": "MINED",
  "match_time": "1746457132",
  "last_update": "1746457158",
  "outcome": "Yes",
  "bucket_index": 0,
  "owner": "185d97e1-816b-d87e-3d81-03e4d4340536",
  "maker_address": "0xF7B5bDa9Ce1c976C6965019aD46906e40C74FC82",
  "transaction_hash": "0x61a664d1561ee23f6dbb3c5d83a28c070af9d8bdabe9c808b9fb3b373eee34a0",
  "maker_orders": [
    {
      "order_id": "0x8a74d2818e13c4bbd4eb34e611bdfd3bcd6d6b7dec4644a89eb7be62b840602b",
      "owner": "ca85b7c3-e243-849b-f4f8-56a280a12923",
      "maker_address": "0x51373c6B56e4a38bF97c301efbfF840fc8451556",
      "matched_amount": "4",
      "price": "0.25",
      "fee_rate_bps": "0",
      "asset_id": "93124055671959869958037846065354081314545895099992000276527130498502400601286",
      "outcome": "Yes"
    }
  ],
  "trader_side": "TAKER"
}
```

## Key Data Fields Explained

- **id**: Unique identifier for the trade
- **market**: Contract address for the market
- **asset_id**: Token ID representing the specific outcome being traded
- **side**: Direction of the trade ("BUY" or "SELL")
- **size**: Amount of shares traded
- **price**: The price per share in USDC
- **outcome**: The specific outcome being traded (e.g., "Yes" or "No")
- **status**: Status of the transaction (e.g., "MINED")
- **match_time**: Timestamp when the trade was matched
- **maker_address**: Address of the liquidity provider
- **transaction_hash**: Blockchain transaction hash
- **trader_side**: Role in the trade ("MAKER" or "TAKER")

## Troubleshooting

### Common Issues

1. **TypeError: keys must be str, int, float, bool or None, not date**: This is fixed in the latest version - make sure you're using the current code
2. **Authentication Error**: Make sure your WALLET_PRIVATE_KEY is correctly set in the .env file
3. **Import Error**: Ensure you're using the correct import paths, especially when running from different directories
4. **No Data**: If no trades are found, try using a different wallet address or check if you have any maker trades
5. **AttributeError: 'DataFrame' object has no attribute 'sorted_values'**: This bug is fixed in the latest version

### Example Commands

```bash
# Quick run from project root directory
python -m src.polymarket.trade_analysis.run

# Get only trades for a specific market
python -c "from src.polymarket.trade_analysis import PolymarketTradeAnalyzer; \
           analyzer = PolymarketTradeAnalyzer(); \
           trades = analyzer.get_trades_by_market('0x7bedaca7d17a565de42bbf4c0e25535396350bc6026adf1e6c633e3d42aadf63'); \
           print(len(trades))"
```

## Additional Examples

### Basic Trade Analysis

```python
from src.polymarket.trade_analysis import PolymarketTradeAnalyzer

# Initialize the analyzer
analyzer = PolymarketTradeAnalyzer()

# Get trades where you are the maker
your_trades = analyzer.get_trades_by_maker()

# Convert to pandas DataFrame for analysis
trades_df = analyzer.get_trades_to_dataframe(your_trades)

# Get comprehensive analysis of your trades
analysis = analyzer.get_comprehensive_analysis(your_trades)
print(analysis)
```

### Visualizing Trade Data

```python
from src.polymarket.trade_analysis import PolymarketTradeAnalyzer, PolymarketTradeVisualizer

# Initialize analyzer and get trade data
analyzer = PolymarketTradeAnalyzer()
trades = analyzer.get_trades_by_maker()
trades_df = analyzer.get_trades_to_dataframe(trades)

# Initialize visualizer with a custom output directory
visualizer = PolymarketTradeVisualizer(output_dir='my_visualizations')

# Create price history chart
visualizer.plot_price_history(trades_df)

# Create volume distribution chart
visualizer.plot_volume_distribution(trades_df, by='outcome')

# Create trading activity heatmap
visualizer.plot_trade_heatmap(trades_df)

# Create a comprehensive dashboard
visualizer.plot_trade_dashboard(trades_df, market_name="Example Market")

print("Visualizations saved to the 'my_visualizations' directory")
```

### Data Analysis Options

The `PolymarketTradeAnalyzer` provides several analysis methods:

- **Price Analysis**: Mean, median, min, max, volatility
- **Volume Analysis**: Total volume, mean trade size, volume by outcome
- **Timing Analysis**: Trade frequency, patterns by day/hour
- **Comprehensive Analysis**: All of the above plus additional metrics

### Visualization Options

The `PolymarketTradeVisualizer` provides several visualization methods:

- **Price History**: Line charts of price over time
- **Volume Distribution**: Bar charts of trading volume by outcome or side
- **Price Distribution**: Histograms of trade prices
- **Trading Activity Heatmap**: Heat maps of trading activity by day and hour
- **Trade Dashboard**: A comprehensive dashboard combining multiple visualizations

## Sample Analysis Results

The comprehensive analysis returns detailed metrics in this format:

```python
{
    'trade_count': 42,
    'unique_markets': 3,
    'unique_assets': 5,
    'side_distribution': {'BUY': 28, 'SELL': 14},
    'outcome_distribution': {'Yes': 32, 'No': 10},
    'price_analysis': {
        'mean_price': 0.35,
        'median_price': 0.27,
        'min_price': 0.12,
        'max_price': 0.75,
        'price_volatility': 0.14,
        'price_by_outcome': {'Yes': 0.32, 'No': 0.43}
    },
    'volume_analysis': {
        'total_volume': 432.0,
        'mean_trade_size': 10.29,
        'max_trade_size': 50.0,
        'volume_by_outcome': {'Yes': 312.0, 'No': 120.0},
        'volume_by_side': {'BUY': 280.0, 'SELL': 152.0}
    },
    'timing_analysis': {
        'first_trade_time': '2023-09-15T12:34:56',
        'last_trade_time': '2023-10-21T09:22:14',
        'avg_time_between_trades': 8642.5,
        'max_time_between_trades': 43200.0,
        'trade_count_by_day': {'2023-09-15': 12, '2023-09-16': 8}
    },
    'status_distribution': {'MINED': 42}
}
```

## Features

- Trade retrieval from Polymarket CLOB API
- Comprehensive trade analysis
- Visualization of trade data
- Balance tracking
- Trade summary tables
- Position analysis and PnL tracking

## Position Analysis

The trade analyzer now includes position tracking functionality that helps you understand your trading performance for each market position. It:

1. Groups trades by market/outcome
2. Tracks buy and sell pairs chronologically
3. Identifies complete (closed) vs. partial (open) positions
4. Calculates realized PnL for closed positions
5. Shows exact market names and descriptions
6. Calculates partial realized PnL for positions where you've sold some shares
7. Displays remaining shares and estimated value
8. Fetches current bid and ask prices from Polymarket
9. Calculates potential PnL if sold at current bid price
10. Provides performance metrics with ROI calculation
11. Detects finished markets and adjusts valuations accordingly

### Position Analysis Features

- **Market Names**: Displays full market names fetched from Polymarket API
- **Partial PnL**: Calculates PnL for the portion of shares you've already sold
- **Remaining Shares**: Clearly shows how many shares you still have in each position
- **Current Prices**: Shows both the current bid price (what you can sell for) and ask price (market price)
- **Market Status**: Detects and labels finished markets
- **Performance Metrics**: Displays ROI, unrealized PnL, and status indicators for each position
- **Potential PnL**: Calculates potential profit/loss if you sold at current bid price
- **Active Market Filter**: Option to show only positions for the currently active market
- **Portfolio Summary**: Provides a comprehensive overview of your total realized and unrealized PnL

### How to Use Position Analysis

You can run the position analysis in several ways:

#### Option 1: Using the Dedicated Positions Script (Recommended)

Use this dedicated script that focuses only on position tracking and PnL:

```bash
# Show all positions
python -m src.polymarket.trade_analysis.positions

# Show only active market positions (based on dates in constants.py)
python -m src.polymarket.trade_analysis.positions --active
# OR shorter version
python -m src.polymarket.trade_analysis.positions -a
```

This provides the cleanest view of your positions without any other trade analysis data.

#### Option 2: Using the Main Script with Positions Flag

Use the main script with the positions flag to see only position information:

```bash
python -m src.polymarket.trade_analysis.run positions
```

#### Option 3: As Part of Full Analysis

Run the full analysis script which includes position information at the end:

```bash
python -m src.polymarket.trade_analysis.run
```

### Example Output

```
=== Polymarket Position Analysis ===
Initializing trade analyzer...
Connected to Polymarket CLOB API with wallet: 0xF7B5bD...

Retrieving your trades...
Found 31 trades. Analyzing positions...
Fetching market names and current prices...

=== Position Analysis ===
Found 9 positions (8 open, 1 closed)

=== Position Details ===
1. Market: Will Elon tweet 100–124 times May 23–30?
   ID: 0xe63332b05d45de8f89340ed0742426b29e8a86207f6c7bcd0107fad9e97450bf
   Outcome: Yes | Status: OPEN (Profitable)
   Entry: 2025-05-26 14:56:17 | Exit: OPEN
   Buy Volume: 24.48 @ Avg Price: $0.1226
   Sell Volume: 0.00 @ Avg Price: $0.0000
   Current Bid Price (Selling): $0.1300
   Current Ask Price (Market): $0.1400
   Remaining Shares: 24.48
   Est. Value at Market (Ask) Price: $3.4272
   Unrealized PnL: $0.4267
   Total PnL: $0.4267 (ROI: 14.26%)
   Potential PnL if Sold Now: $0.1815

2. Market: Will Elon tweet 250–274 times May 2–9?
   ID: 0x7bedaca7d17a565de42bbf4c0e25535396350bc6026adf1e6c633e3d42aadf63
   Outcome: Yes | Status: CLOSED (Closed)
   Market Status: FINISHED
   Entry: 2025-05-05 18:57:21 | Exit: 2025-05-06 23:11:47
   Buy Volume: 8.00 @ Avg Price: $0.2500
   Sell Volume: 8.00 @ Avg Price: $0.2650
   Current Bid Price (Selling): $0.0000
   Current Ask Price (Market): $0.0000
   Remaining Shares: 0.00
   Realized PnL: $0.1200
   Total PnL: $0.1200 (ROI: 6.00%)

=== Portfolio Summary ===
Total Realized PnL: $3.0219
  - From Closed Positions: $0.1200
  - From Partial Sells: $2.9019
Total Unrealized PnL: $0.7548
Total PnL (Realized + Unrealized): $3.7767
Portfolio Value: $4.9562
Total Remaining Shares: 27.09
Closed Positions: 1
Open Positions: 8
```
