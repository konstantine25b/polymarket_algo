# Polymarket Position Tracker with Profit/Loss Analytics

A powerful tool for tracking, analyzing, and visualizing your Polymarket positions with comprehensive profit and loss calculations.

## Features

- **Detailed Position Analysis**: Track current position sizes for each outcome in each market
- **Full Market Information**: Display complete market names and details with full market IDs
- **Profit/Loss Calculations**: Calculate realized and unrealized P&L for each trade, outcome, and market
- **Performance Metrics**: Track ROI (Return on Investment) across your entire portfolio
- **Trade Analytics**: Analyze trade history with detailed profit/loss information
- **Rich Visualizations**: Generate bubble charts, trade history plots, and market-specific visualizations
- **Tabular Views**: Display formatted tables of positions and trades with P&L metrics
- **Data Export**: Export position and trade data to CSV files with comprehensive P&L information
- **Interactive Exploration**: Interact with visualizations and analyze your trading performance
- **Smart Market ID Display**: Intelligently display full market IDs without duplication
- **Robust Market Data Retrieval**: Use multiple API endpoints with graceful fallbacks
- **Table Image Generation**: Save position tables as high-quality PNG images for sharing or reporting
- **Simple Position Format**: Quickly get a basic dictionary of market IDs and share quantities

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up your Polymarket wallet private key in a `.env` file

## Configuration

Create a `.env` file in the root directory with the following:

```
WALLET_PRIVATE_KEY=your_private_key_here
```

## Usage

### From Python

```python
from src.polymarket.my_positions.position_tracker import PolymarketPositionTracker

# Initialize tracker
tracker = PolymarketPositionTracker()

# Get position summary with P&L information
positions = tracker.get_positions_summary()
tracker.print_positions_summary(positions)

# Get simple dictionary of market IDs and share quantities
simple_positions = tracker.get_simple_positions()
print(simple_positions)

# Display positions table with P&L metrics
tracker.display_positions_table()

# Display positions table and save as image
tracker.display_positions_table(save_image=True)

# Display trades by market with P&L analytics
tracker.display_trades_by_market()

# Generate visualizations
tracker.visualize_positions_chart()
tracker.visualize_trade_history()

# Export data with P&L information
tracker.export_positions_table()
tracker.export_trades_by_market()
```

### From Command Line

Display position summary with P&L information:

```bash
python -m src.polymarket.my_positions.cli
```

Display simple list of market IDs and share quantities:

```bash
python -m src.polymarket.my_positions.cli --simple-positions
```

Display detailed position table with P&L metrics:

```bash
python -m src.polymarket.my_positions.cli --positions-table
```

Display position table and save as image:

```bash
python -m src.polymarket.my_positions.cli --positions-table --save-table-image
```

Specify custom image path:

```bash
python -m src.polymarket.my_positions.cli --positions-table --save-table-image --table-image-path /path/to/image.png
```

Display trade history by market with P&L analytics:

```bash
python -m src.polymarket.my_positions.cli --trades-table
```

Generate visualizations:

```bash
python -m src.polymarket.my_positions.cli --visualize --show-plots
```

Export data to CSV files with P&L information:

```bash
python -m src.polymarket.my_positions.cli --export-positions-csv --export-trades-csv
```

## Improved Position Table Features

The position table display provides several enhancements for better readability:

- **Shortened Market IDs**: Uses concise identifiers (M1, M2, etc.) in the table
- **Compact Market Names**: Shortens long market names to fit neatly in the table
- **Market Reference Guide**: Provides a complete reference of full market names and IDs after the table
- **Table Image Generation**: Creates high-quality PNG images of position tables with timestamps
- **Comprehensive P&L**: Displays realized and unrealized profit/loss for each position
- **ROI Calculation**: Shows percentage return on investment for each position and overall

## Profit/Loss Calculation Features

The P&L tracking system provides comprehensive analytics:

### Realized and Unrealized P&L

- **Realized P&L**: Calculate exact profit/loss for completed trades
- **Unrealized P&L**: Estimate current value of open positions based on last known prices
- **Total P&L**: Combined realized and unrealized profit/loss metrics

### Cost Basis Tracking

- Track average cost basis for each position
- Calculate running cost basis as trades are executed
- Maintain accurate inventory levels for each outcome

### ROI Calculations

- Calculate Return on Investment (ROI) as a percentage
- Analyze ROI at the outcome, market, and portfolio levels
- Compare performance across different trades and markets

### P&L Summary Views

- Market-level P&L summaries
- Portfolio-level performance metrics
- Outcome-specific profit and loss analysis

## Example Output

### Position Table with P&L Metrics

```
CURRENT POSITIONS TABLE:

Market ID Market Name     Outcome Position Size Current Price Position Value Cost Basis  Trades Realized P&L Unrealized P&L Total P&L    ROI (%)
       M1 350 or more ★ SUMMARY ★                                      $1.95      $2.00       2        $0.00         $-0.04    $-0.04     -2.09%
                              Yes         84.94       $0.0230          $1.95      $2.00       2        $0.00         $-0.04    $-0.04     -2.09%
       M2     300–324 ★ SUMMARY ★                                      $1.00      $1.00       1        $0.00          $0.00     $0.00     +0.00%
                              Yes          8.20       $0.1220          $1.00      $1.00       1        $0.00          $0.00     $0.00     +0.00%
       M3     200–224 ★ SUMMARY ★                                      $0.02      $0.02       5        $3.48          $0.00     $3.48 +14080.21%
                              Yes          0.32       $0.0790          $0.02      $0.02       5        $3.48          $0.00     $3.48 +14080.21%
       M4     275–299 ★ SUMMARY ★                                      $0.77      $0.77       2       $-0.01         $-0.00    $-0.01     -1.30%
                              Yes          3.31       $0.2320          $0.77      $0.77       2       $-0.01         $-0.00    $-0.01     -1.30%

PORTFOLIO SUMMARY:
  Total Position Value: $3.75
  Total Realized P&L: $3.59
  Total Unrealized P&L: $-0.04
  Total P&L: $3.55
  Overall ROI: +93.78%

MARKET REFERENCE GUIDE:
  M1: Will Elon tweet 350 or more times May 2–9?
     ID: 0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de49fc653ce6e1999f
  M2: Will Elon tweet 300–324 times May 2–9?
     ID: 0x594df4f4d61ebafbd334fc5f3af9fe5ad382daccbf99dc83eeac8f33d1810ef6
  M3: Will Elon tweet 200–224 times May 2–9?
     ID: 0x820cb7e640e07ba871c249db6d17ec0a56c2a6c866fcf5167ceb7e2b3faa6b02
  M4: Will Elon tweet 275–299 times May 2–9?
     ID: 0xb942003e5c182f905b88302b79368d7891a2d3d418a13f884a52e727e4effb95
```

### Simple Positions Output

```
SIMPLE POSITIONS (Market ID -> Outcome -> Share Quantity):

Will Elon tweet 350 or more times May 2–9? (0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de49fc653ce6e1999f):
  Yes: 84.940000 shares

Will Elon tweet 300–324 times May 2–9? (0x594df4f4d61ebafbd334fc5f3af9fe5ad382daccbf99dc83eeac8f33d1810ef6):
  Yes: 8.200000 shares

Will Elon tweet 200–224 times May 2–9? (0x820cb7e640e07ba871c249db6d17ec0a56c2a6c866fcf5167ceb7e2b3faa6b02):
  Yes: 0.320000 shares

Will Elon tweet 275–299 times May 2–9? (0xb942003e5c182f905b88302b79368d7891a2d3d418a13f884a52e727e4effb95):
  Yes: 3.310000 shares
```

### Programmatic Usage of Simple Positions

```python
from src.polymarket.my_positions.position_tracker import PolymarketPositionTracker

# Initialize tracker
tracker = PolymarketPositionTracker()

# Get simple dictionary of market IDs and share quantities
simple_positions = tracker.get_simple_positions()

# Example of the returned data structure:
# {
#    '0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de49fc653ce6e1999f': {'Yes': 84.94},
#    '0x594df4f4d61ebafbd334fc5f3af9fe5ad382daccbf99dc83eeac8f33d1810ef6': {'Yes': 8.2},
#    '0x820cb7e640e07ba871c249db6d17ec0a56c2a6c866fcf5167ceb7e2b3faa6b02': {'Yes': 0.32},
#    '0xb942003e5c182f905b88302b79368d7891a2d3d418a13f884a52e727e4effb95': {'Yes': 3.31}
# }

# Process the data programmatically
for market_id, outcomes in simple_positions.items():
    print(f"Market: {market_id}")
    for outcome, quantity in outcomes.items():
        print(f"  {outcome}: {quantity} shares")
```

### Trades Table with P&L Analytics

```
TRADES BY MARKET (Total: 20 trades across 2 markets):

--- Market: Will Elon tweet 350 or more times May 2–9? (0x14ebc0ede61a12aaad2da1c7c591376ab8a61b9e71c671de49fc653ce6e1999f) ---
  Outcome    Time                 Price    Size  Side  Impact  P&L ($)   P&L (%)   Avg Cost
--------------------------------------------------------------------------------------
  Yes      2024-05-01 10:15:32  $0.0220    5.0   Buy   +5.0
  Yes      2024-05-15 14:22:45  $0.0230    5.0   Buy   +5.0   $0.00     +0.00%    $0.0225

Market P&L Summary:
  Realized P&L: $0.00
  Unrealized P&L: $-0.04
  Total P&L: $-0.04
  ROI: -2.09%

OVERALL PORTFOLIO P&L SUMMARY:
  Realized P&L: $3.59
  Unrealized P&L: $-0.04
  Total P&L: $3.55
  ROI: +93.78%
```

## How It Works

The profit and loss calculation system:

1. **Tracks Every Trade**: Records the price, size, and side of each trade
2. **Maintains Inventory**: Keeps running totals of your position in each outcome
3. **Calculates Cost Basis**: Determines the average cost of your current positions
4. **Computes Realized P&L**: Calculates profit/loss when positions are reduced
5. **Estimates Unrealized P&L**: Values current positions at their last known price
6. **Aggregates Metrics**: Combines data at the outcome, market, and portfolio levels

For detailed information on the API and implementation, refer to the source code documentation.
