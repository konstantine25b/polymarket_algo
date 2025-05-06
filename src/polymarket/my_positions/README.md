# Polymarket Position Tracker

A simple tool to track and analyze your current positions on Polymarket based on your trade history.

## Overview

This module analyzes your Polymarket trade history to calculate your current positions across all markets you've traded in. It provides:

- Current position sizes for each outcome in each market
- **Full market IDs** displayed intelligently (no duplication)
- Robust market data retrieval with fallback mechanisms
- Full market names and details where available
- Trade history visualization and analysis
- Bubble chart visualization of current positions
- Market-specific trade history analysis
- Tabular view of positions and trade history
- CSV export of position and trade data
- Interactive visualizations of your positions
- Position summary reporting
- JSON export of position data

## Usage

### From Python

```python
from src.polymarket.my_positions import PolymarketPositionTracker

# Initialize with default settings (loads wallet key from .env)
tracker = PolymarketPositionTracker()

# Get detailed position information
positions = tracker.get_detailed_positions()

# Print a readable summary
tracker.print_positions_summary(positions)

# Display positions as a formatted table
tracker.display_positions_table(positions)

# Display all trades grouped by market
tracker.display_trades_by_market()

# Export to CSV files
tracker.export_positions_table(positions)
tracker.export_trades_by_market()

# Generate all visualizations
tracker.visualize_positions(positions, save=True, show=True)

# Generate a bubble chart of positions
tracker.visualize_positions_chart(positions, save=True, show=True)

# Visualize your complete trade history
trades = tracker.get_my_trades()
trades_df = tracker.trades_to_dataframe(trades)
tracker.visualize_trade_history(trades_df, save=True, show=True)

# Visualize trades for a specific market
tracker.visualize_market_trades(market_id="YOUR_MARKET_ID", save=True, show=True)

# Save to a JSON file
tracker.save_positions_to_file(positions)
```

### From Command Line

The module includes a command-line interface with multiple options for visualizations and data export:

```bash
# Get all positions
python -m src.polymarket.my_positions.cli

# Get positions for a specific market
python -m src.polymarket.my_positions.cli --market YOUR_MARKET_ID

# Display positions as a formatted table
python -m src.polymarket.my_positions.cli --positions-table

# Display all trades grouped by market
python -m src.polymarket.my_positions.cli --trades-table

# Export positions to CSV
python -m src.polymarket.my_positions.cli --export-positions-csv

# Export trades by market to CSV
python -m src.polymarket.my_positions.cli --export-trades-csv

# Specify CSV export directory
python -m src.polymarket.my_positions.cli --export-positions-csv --csv-dir /path/to/csv/dir

# Save results to a file
python -m src.polymarket.my_positions.cli --save

# Generate all visualizations
python -m src.polymarket.my_positions.cli --visualize

# Show plots interactively
python -m src.polymarket.my_positions.cli --show-plots

# Generate a bubble chart of your positions
python -m src.polymarket.my_positions.cli --positions-chart

# Visualize your complete trade history
python -m src.polymarket.my_positions.cli --trade-history

# Visualize trades for a specific market
python -m src.polymarket.my_positions.cli --market-trades YOUR_MARKET_ID

# Combine multiple options
python -m src.polymarket.my_positions.cli --positions-table --trades-table --export-positions-csv --export-trades-csv

# Enable verbose logging
python -m src.polymarket.my_positions.cli --verbose
```

## Configuration

The position tracker gets your wallet private key from the `.env` file by default. Make sure you have the following environment variable set:

```
WALLET_PRIVATE_KEY=your_private_key_here
```

Alternatively, you can provide the key directly when initializing the tracker or through the command-line interface.

## Example Output

The position tracker outputs a summary like:

```
POLYMARKET POSITIONS SUMMARY - 0x123456789abcdef...
Last Updated: 2023-05-25T14:30:45.123456
Active Markets: 3
Total Trades: 42

CURRENT POSITIONS:

Will Bitcoin exceed $100k in 2023? (0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de49fc653ce6e1999f):
  • Yes: +100.00 shares (15 trades)
  • No: -50.00 shares (8 trades)

US 2024 Presidential Election (0x594df4f4d61ebafbd334fc5f3af9fe5ad382daccbf99dc83eeac8f33d1810ef6):
  • Trump: +25.00 shares (5 trades)
  • Biden: -10.00 shares (3 trades)
```

### Table Output

When using the `--positions-table` option, you'll get a nicely formatted table of your current positions with full market IDs:

```
CURRENT POSITIONS TABLE:

         Market ID                                            |                Market Name                 | Outcome | Position Size | Trades
-----------------------------------------------------------|-------------------------------------------|---------|---------------|-------
0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de49fc... | Will Bitcoin exceed $100k in 2023?        | Yes     | 100.00        | 15
0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de49fc... | Will Bitcoin exceed $100k in 2023?        | No      | -50.00        | 8
0x594df4f4d61ebafbd334fc5f3af9fe5ad382daccbf99dc83eeac... | US 2024 Presidential Election             | Trump   | 25.00         | 5
0x594df4f4d61ebafbd334fc5f3af9fe5ad382daccbf99dc83eeac... | US 2024 Presidential Election             | Biden   | -10.00        | 3

Total positions: 4
```

Using `--trades-table` provides a detailed breakdown of all trades by market with complete market IDs:

```
TRADES BY MARKET (Total: 31 trades across 3 markets):

--- Market: Will Bitcoin exceed $100k in 2023? (0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de49fc653ce6e1999f) ---
  Market ID                                              |        Market Name        | Outcome |       Time       | Price | Size |  Side  | Impact
------------------------------------------------------|---------------------------|---------|------------------|-------|------|--------|-------
0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de... | Will Bitcoin exceed $... | Yes     | 2023-05-20 10:15 | 0.65  | 50.0 | BUY    | 50.0
0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de... | Will Bitcoin exceed $... | Yes     | 2023-05-21 14:30 | 0.70  | 50.0 | BUY    | 50.0
0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de... | Will Bitcoin exceed $... | No      | 2023-05-22 09:45 | 0.30  | 50.0 | SELL   | -50.0
Total: 23 trades
```

## Visualization Features

The module offers several types of visualizations, all with full market IDs displayed:

1. **Position Size by Market (Pie Chart)** - Shows the distribution of your position sizes across different markets.

2. **All Positions by Size (Bar Chart)** - Horizontal bar chart of all positions sorted by size, with complete market IDs.

3. **Position Bubble Chart** - Visual overview of your positions where:

   - Y-axis represents position size
   - Bubble size represents number of trades
   - Colors differentiate between markets
   - Labels show outcomes and position sizes
   - Includes full market IDs in the legend

4. **Trade History Visualization** - Visual representation of your trading activity over time, showing:

   - Buy transactions (upward triangle markers)
   - Sell transactions (downward triangle markers)
   - Price points for each transaction
   - Trade details on hover or click
   - Color-coding by market

5. **Market-Specific Trade History** - Detailed visualization of all your trades within a specific market:

   - Timeline of your trades
   - Price movement visualization
   - Buy/sell activity comparison
   - Trade size representation
   - Complete transaction details

6. **Position Summary Dashboard** - A comprehensive dashboard with multiple visualizations including:
   - Position distribution
   - Top positions
   - Trade activity history
   - Tabular data of all positions with full market IDs

## Data Export Features

The module provides several ways to export and view your data:

1. **Position Table Display** - Formatted table showing your current positions sorted by size.

2. **Trade History Table** - Comprehensive view of all trades grouped by market with timestamps and transaction details.

3. **CSV Export of Positions** - Export your current position data to a CSV file for further analysis in spreadsheet applications.

4. **CSV Export of Trades** - Export your complete trade history grouped by market to a CSV file.

5. **JSON Export** - Save position data with detailed market information to a JSON file.

All exports include full market IDs, prices, sizes, and timestamps where available. CSV files are saved in the `output/tables` directory by default, but you can specify a custom location.

## Important Features

- **Smart Market ID Display** - Market IDs are displayed in full but only when needed (avoiding duplication)
- **Robust Market Data Retrieval** - Multiple API endpoints are tried with graceful fallbacks if market info is unavailable
- **Trade History** - Visualize your trading activity over time with buy/sell indicators
- **Trade Counts** - Position summaries now include the number of trades for each position
- **Market-Specific Analysis** - View trade history for a specific market of interest
- **Position Bubble Chart** - Intuitive visualization of your positions with size, market, and trade count representation
- **Tabular Data** - View your positions and trades in neatly formatted tables
- **Data Export** - Export to CSV for further analysis in spreadsheet applications

## How It Works

This module:

1. Connects to the Polymarket CLOB API using your wallet credentials
2. Fetches your trade history (as both maker and taker)
3. Attempts to fetch full market names and details from multiple Polymarket API endpoints
4. Uses fallback mechanisms if market information is unavailable
5. Calculates your net position for each outcome in each market
6. Shows only non-zero positions (outcomes where you currently hold shares)
7. Generates visualizations and tabular views of your positions and trade history
8. Exports data in various formats (JSON, CSV) for further analysis
9. Displays full market IDs intelligently (avoiding duplication)

The implementation accounts for:

- Whether you were the maker or taker in a trade
- Whether you were buying or selling in each trade
- Net position after multiple trades in the same outcome
- Time-based analysis of your trading activity
- Trade frequency and volume across markets

## Dependencies

- `pandas`: For data manipulation and table display
- `matplotlib`: For generating visualizations
- `py_clob_client`: For interfacing with Polymarket's CLOB API
- `python-dotenv`: For loading environment variables
- `requests`: For fetching market information

## Notes

- Position calculations account for both buy and sell trades, as well as maker and taker roles
- Only non-zero positions are included in the output
- The tracker calls the Polymarket API directly to fetch full market names and details
- Visualizations are created using Matplotlib and saved as PNG files
- Full market IDs are preserved in all outputs for accurate identification
- Trade history visualization shows your trading activity over time
- The bubble chart visualization provides an intuitive overview of your positions
- Tables and CSV exports provide detailed breakdowns for further analysis
