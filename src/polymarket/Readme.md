# Polymarket Data Analyzer

A comprehensive toolkit for fetching, analyzing, and visualizing prediction market data from Polymarket events.

## Overview

This module allows you to:

1. Generate visualizations of market probabilities
2. Fetch current market probabilities from any Polymarket event
3. Fetch order book data with real buy and sell orders (optional)
4. Store the data in structured JSON and CSV formats
5. Save and visualize order book data with buy/sell orders
6. Track and compare changes in market sentiment over time

## How to Run

You can run the Polymarket Data Analyzer using Python directly:

```bash
# Activate virtual environment
source venv/bin/activate

# Run with default event URL (Elon Musk tweets)
python3 -m src.polymarket.main

# Run with specific Polymarket event URL
python3 -m src.polymarket.main --url "https://polymarket.com/event/your-event-slug"

# Generate visualization plots
python3 -m src.polymarket.main --generate-plot

# Fetch and display order book data
python3 -m src.polymarket.main --order-frames

# Fetch, display, save, and visualize order book data
python3 -m src.polymarket.main --order-frames --save-orders --visualize-orders

# See detailed order book information
python3 -m src.polymarket.main --order-frames --detailed-orders

# Save data to files
python3 -m src.polymarket.main --save-data

# Compare with previous data
python3 -m src.polymarket.main --save-data --compare

# List stored events
python3 -m src.polymarket.main --list-events
```

By default, the analyzer displays market percentages for the Elon Musk tweets event without fetching order book data (which can be time-consuming).

## Command Line Options

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

## Understanding the Output

### Default Output

The default output provides:

1. **Market Percentages**: Shows the probability for each market outcome (sorted highest to lowest)

Example:

```
Event: Elon Musk # of tweets April 11-18?

Market Percentages:
47.5% - Will Elon tweet 150–174 times April 11–18?
30.2% - Will Elon tweet 175–199 times April 11–18?
7.1% - Will Elon tweet 100–124 times April 11–18?
5.0% - Will Elon tweet less than 100 times April 11–18?
...
```

### Order Book Data (with --order-frames)

When using the `--order-frames` option, you'll see:

2. **Order Book Information**: Displays top 5 buy and sell orders for each market, including:
   - Indication of whether the data is real or synthetic
   - Price (in cents)
   - Size (number of contracts)
   - Total value (in dollars)
   - Market spread information

Example:

```
== Will Elon tweet 125–149 times April 11–18? ==
[REAL MARKET DATA]

BUY ORDERS (Bids) - Top 5
Price      Size  Total
-------  ------  -------
97.9¢    251.00  $245.74
97.8¢    600.00  $586.80
97.4¢    154.15  $150.14
97.3¢    100.00  $97.30
97.2¢     20.00  $19.44

SELL ORDERS (Asks) - Top 5
Price      Size  Total
-------  ------  -------
98.2¢     23.51  $23.09
98.5¢     62.58  $61.64
98.7¢     43.14  $42.58
99.0¢     33.76  $33.42
99.2¢     11.72  $11.63

Market Spread: 0.3¢ (0.31%)
```

The system will attempt to fetch real order book data through Polymarket's API. When real data is unavailable, it falls back to generating synthetic order data based on actual market prices (clearly marked as "SYNTHETIC DATA").

### Order Book Visualizations (with --visualize-orders)

When using the `--visualize-orders` option along with `--order-frames`, the analyzer will:

1. Generate bar chart visualizations for each market's order book
2. Show buy orders (green) and sell orders (red) with their respective sizes
3. Highlight the bid-ask spread
4. Save the visualizations to `src/polymarket/plots/order_books/`

### Visualizations (--generate-plot)

The visualization shows the probability for each market outcome as a bar chart:

- **X-axis**: The market questions
- **Y-axis**: The probability percentage (from 0% to 100%)
- **Labels**: Each bar is labeled with its exact percentage value

For comparison plots (--compare), you'll see both current and previous probabilities side by side.

## Output Files

When using various save options, the analyzer produces the following outputs:

- **Market Data JSON**: `src/polymarket/data/json/{event_slug}_{timestamp}.json`
- **Market Data CSV**: `src/polymarket/data/csv/{event_slug}_{timestamp}.csv`
- **Order Book Data**: `src/polymarket/data/order_books/{event_slug}_orderbook_{timestamp}.json`
- **Market Probability Plot**: `src/polymarket/plots/{event_slug}_probabilities.png`
- **Order Book Visualizations**: `src/polymarket/plots/order_books/{event_slug}_{question}_{timestamp}.png`
- **Comparison Plot**: `src/polymarket/plots/{event_slug}_comparison.png` (when using --compare)

## Example Use Cases

### Tracking Elon Musk's Tweet Predictions

```bash
# Get current odds on Elon Musk's tweet count
python3 -m src.polymarket.main

# Save the data
python3 -m src.polymarket.main --save-data

# Generate a visualization
python3 -m src.polymarket.main --generate-plot

# Later, compare how odds have changed
python3 -m src.polymarket.main --save-data --compare --generate-plot
```

### Analyzing Market Liquidity and Order Books

```bash
# View order book data for all markets
python3 -m src.polymarket.main --order-frames

# View detailed order book including all orders
python3 -m src.polymarket.main --order-frames --detailed-orders

# Save and visualize order book data
python3 -m src.polymarket.main --order-frames --save-orders --visualize-orders
```

### Visualizing Probability Distributions

```bash
# Generate a visualization of the current probabilities
python3 -m src.polymarket.main --generate-plot
```

## Troubleshooting

If you encounter issues:

1. Ensure you have Python 3.6+ installed
2. Verify that you have the required dependencies:
   ```bash
   pip install requests matplotlib pandas tabulate py-clob-client
   ```
3. Check that the Polymarket URL is correct
4. Ensure you have an active internet connection
5. For order book data:
   - If you see "[SYNTHETIC DATA]" for a market, this means the system couldn't fetch real order data and generated synthetic data instead
   - If you want to force synthetic data (for testing), temporarily disconnect from the internet
