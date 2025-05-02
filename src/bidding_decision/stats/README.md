# Market Prediction Comparison Tool

A sophisticated tool to compare predictions from the Prophet model with actual Polymarket order book data and identify trading opportunities.

## Features

- Fetches data from both Prophet predictions and Polymarket order book
- Normalizes range names between different data sources to ensure proper matching
- Includes all critical market prices: Market midpoint, Bid, and Ask
- Calculates difference between prediction and ask price (prediction - ask)
- Identifies potential "edge" in market prices relative to predictions
- Provides threshold-adjusted opportunity values for realistic trading decisions
- Allows filtering by a minimum threshold to focus on significant opportunities
- Visualizes comparisons with detailed bar charts and comprehensive dashboards
- Provides specific trading recommendations with exact prices
- Automatically saves results to timestamped files

## Usage

### Basic Comparison

```bash
# Run basic comparison with default settings
python -m src.bidding_decision.stats

# Save comparison to specific CSV file
python -m src.bidding_decision.stats --output my_comparison.csv

# Don't refresh market data (use cached data)
python -m src.bidding_decision.stats --no-refresh

# Use enhanced algorithm instead of Prophet
python -m src.bidding_decision.stats --no-prophet

# Only show opportunities with at least 5% difference and apply as threshold
python -m src.bidding_decision.stats --threshold 5.0
```

### With Visualization

```bash
# Generate standard visualization
python -m src.bidding_decision.stats --visualize

# Generate enhanced visualization dashboard with multiple charts
python -m src.bidding_decision.stats --visualize --enhanced-viz

# Save visualization to specific file
python -m src.bidding_decision.stats --visualize --viz-output my_comparison.png

# Generate enhanced visualization with 3% threshold for meaningful opportunities
python -m src.bidding_decision.stats --visualize --enhanced-viz --threshold 3.0
```

### Output Example

```
Comparison Table:
           Range  Prediction (%)  Market (%)  Bid (%)  Ask (%)  Difference (%)  Opportunity (%)  Adj. Opportunity (3.0%)
        150–174           95.58        89.5     89.0     90.0            5.58            5.58                      2.58
        175–199            3.65         9.5      9.0     10.0           -6.35            6.35                      3.35
        200–224            0.48        0.15      0.0      0.5           -0.02            0.02                      0.00
        225–249            0.14         0.0      0.0      0.5           -0.36            0.36                      0.00
        250–274            0.09         0.0      0.0      0.5           -0.41            0.41                      0.00
        275–299            0.02         0.0      0.0      0.5           -0.48            0.48                      0.00
        300–324            0.01         0.0      0.0      0.5           -0.49            0.49                      0.00
        325–349             0.0         0.0      0.0      0.5           -0.50            0.50                      0.00
        350–374            0.01         0.0      0.0      0.5           -0.49            0.49                      0.00
        375–399             0.0         0.0      0.0      0.5           -0.50            0.50                      0.00
    400 or more            0.02         0.0      0.0      0.5           -0.48            0.48                      0.00
 less than 100             0.0         0.0      0.0      0.5           -0.50            0.50                      0.00
        100–124             0.0         0.0      0.0      0.5           -0.50            0.50                      0.00
        125–149             0.0         0.0      0.0      0.5           -0.50            0.50                      0.00
  EXPECTED VALUE         163.47      163.07     N/A     N/A            0.40            0.40                      0.00

Best Trading Opportunity:
Range: 175–199
Prediction: 3.65%
Market: 9.5%
Bid: 9.0%
Ask: 10.0%
Difference: -6.35%
Opportunity: 6.35%
Adjusted Opportunity: 3.35%
Recommendation: SELL 175–199 at 9.0% (prediction: 3.65%)
Edge: 3.35% after 3.0% threshold
```

## Understanding the Output

- **Range**: The outcome range in the market (e.g., "150-174 tweets")
- **Prediction (%)**: The probability predicted by the model
- **Market (%)**: The midpoint between bid and ask prices
- **Bid (%)**: The price you can sell at
- **Ask (%)**: The price you can buy at
- **Difference (%)**: Prediction minus Ask (for buy opportunities) or Prediction minus Bid (for sell opportunities)
- **Opportunity (%)**: The absolute value of the difference
- **Adj. Opportunity (X%)**: The opportunity after subtracting your minimum threshold

The tool uses ask prices for buy opportunities and bid prices for sell opportunities to provide realistic trading recommendations based on actual executable prices, not theoretical midpoints.

## Visualization Options

### Standard Visualization

The standard visualization includes:

- Bar chart comparing prediction vs market probabilities
- Bar chart of trading opportunities

### Enhanced Visualization Dashboard

The enhanced visualization (`--enhanced-viz`) creates a comprehensive dashboard with:

- Probability comparison between prediction and market
- Bid-Ask spread analysis
- Top trading opportunities sorted by edge
- Expected value comparison
- Detailed trading recommendations table
- Color-coded buy/sell indicators
- Summary of the best trading opportunity

This dashboard provides a complete overview of all potential opportunities and helps identify the most profitable trades at a glance.

## Output Files

By default, the tool will save output files to these locations:

- Comparison CSV files: `src/bidding_decision/stats/output/comparison_TIMESTAMP.csv`
- Visualization images: `src/bidding_decision/stats/output/viz/comparison_TIMESTAMP.png`

Where `TIMESTAMP` is the current date and time.

## Python API

You can also use the tool programmatically:

```python
from src.bidding_decision.stats.comparison import generate_comparison_table, visualize_comparison, enhanced_visualization

# Generate comparison table
df = generate_comparison_table(
    refresh=True,           # Refresh market data
    use_prophet=True,       # Use Prophet for predictions
    threshold=2.0,          # Only show opportunities > 2%
    output_path='comparison.csv'  # Save to CSV
)

# Standard visualization
visualize_comparison(
    comparison_df=df,       # Use existing dataframe
    threshold=2.0,          # Minimum threshold
    output_path='comparison.png'  # Save visualization
)

# Enhanced visualization dashboard
enhanced_visualization(
    comparison_df=df,       # Use existing dataframe
    threshold=2.0,          # Minimum threshold
    output_path='enhanced_comparison.png'  # Save visualization
)
```

## Command-line Arguments

```
--output PATH      Path to save the comparison table CSV
--no-refresh       Do not refresh market data (use cached)
--no-prophet       Do not use Prophet for predictions (use enhanced algorithm)
--visualize        Generate visualization charts
--enhanced-viz     Generate enhanced visualization dashboard with multiple charts
--viz-output PATH  Path to save visualization image
--threshold FLOAT  Minimum opportunity percentage (0-100) to include in results
```

## How It Works

1. The tool runs both the Prophet prediction algorithm and fetches current Polymarket order book data
2. It normalizes range names between the two data sources (e.g., "150–174" and "Will Elon tweet 150–174 times")
3. A comparison table is generated showing the predictions versus market prices (bid, ask, midpoint)
4. The difference is calculated as Prediction - Ask for potential buys and Prediction - Bid for potential sells
5. Opportunity values are calculated as the absolute difference
6. Adjusted opportunity values subtract your specified threshold from the raw opportunity
7. Ranges with opportunity below your threshold are filtered out (if requested)
8. The tool identifies the best trading opportunity based on adjusted opportunity value
9. If visualization is enabled, it creates charts comparing all values and highlighting opportunities
10. All results are saved to files for later reference
