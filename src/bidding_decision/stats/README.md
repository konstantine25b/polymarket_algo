# Market Prediction Comparison Tool

A sophisticated tool to compare predictions from multiple advanced algorithms with actual Polymarket order book data and identify trading opportunities. Supports Facebook Prophet, Neural Prophet, TimesFM, Ensemble methods, and Enhanced variants with reproducible random seed control.

## 🚀 Features

- **Multiple Prediction Algorithms**: Facebook Prophet, Neural Prophet, TimesFM, Ensemble, and Enhanced variants
- **Reproducible Results**: Random seed control for consistent predictions across runs
- **Real-time Market Data**: Fetches live Polymarket order book data with bid/ask spreads
- **Advanced Matching**: Normalizes range names between different data sources
- **Comprehensive Pricing**: Market midpoint, Bid, and Ask prices with spread analysis
- **Edge Detection**: Calculates prediction vs. execution price differences for realistic trading
- **Threshold Filtering**: Adjustable minimum opportunity thresholds for practical trading
- **Multiple Visualizations**: Standard charts, enhanced dashboards, and simple table views
- **Trading Recommendations**: Clear buy/sell signals with specific execution prices
- **Automated Reporting**: Timestamped CSV and image outputs with detailed analysis

## 🎯 Supported Algorithms

### Core Algorithms

| Algorithm          | Description                 | Speed | Accuracy  | Best Use Case         |
| ------------------ | --------------------------- | ----- | --------- | --------------------- |
| `prophet`          | Legacy polymarket_predictor | ~5s   | Good      | Baseline comparison   |
| `facebook_prophet` | Standard Facebook Prophet   | ~8s   | Very Good | General forecasting   |
| `neural_prophet`   | Deep learning time series   | ~30s  | Excellent | Complex patterns      |
| `timesfm`          | Google foundation model     | ~20s  | Excellent | Zero-shot learning    |
| `ensemble`         | Multi-model combination     | ~3min | Maximum   | Best overall accuracy |

### Enhanced Algorithms

| Algorithm                   | Description            | Models Used             | Training Time | Accuracy |
| --------------------------- | ---------------------- | ----------------------- | ------------- | -------- |
| `enhanced_facebook_prophet` | Multi-Prophet ensemble | 5 Prophet variants + RF | ~45s          | Superior |
| `enhanced_neural_prophet`   | Multi-Neural ensemble  | 4 Neural variants       | ~3min         | Superior |
| `enhanced_timesfm`          | Multi-TimesFM ensemble | 4 TimesFM configs       | ~2min         | Superior |

## 📋 Quick Start Commands

### Basic Algorithm Comparison

```bash
# basic
python -m src.bidding_decision.stats.comparison 
# Use Facebook Prophet (recommended for speed)
python -m src.bidding_decision.stats.comparison --algorithm facebook_prophet

# Use Enhanced Facebook Prophet (recommended for accuracy)
python -m src.bidding_decision.stats.comparison --algorithm enhanced_facebook_prophet

# Use Neural Prophet with custom parameters
python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --epochs 100 --learning-rate 0.05

# Use TimesFM foundation model
python -m src.bidding_decision.stats.comparison --algorithm timesfm

# Use Ensemble (all models combined)
python -m src.bidding_decision.stats.comparison --algorithm ensemble --fast-mode
```

### Reproducible Results with Random Seeds

```bash
# Set specific random seed for reproducible results
python -m src.bidding_decision.stats.comparison --algorithm enhanced_timesfm --random-seed 42

# Compare different algorithms with same seed
python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --random-seed 123
python -m src.bidding_decision.stats.comparison --algorithm timesfm --random-seed 123
```

### Advanced Analysis with Thresholds

```bash
# Only show opportunities above 2% threshold
python -m src.bidding_decision.stats.comparison --algorithm enhanced_facebook_prophet --threshold 2.0

# Generate enhanced visualization with 3% threshold
python -m src.bidding_decision.stats.comparison --algorithm ensemble --threshold 3.0 --visualize --enhanced-viz
```

## 🎨 Visualization Options

### Standard Visualization

```bash
# Generate basic charts
python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --visualize

# Save to specific file
python -m src.bidding_decision.stats.comparison --algorithm timesfm --visualize --viz-output my_analysis.png
```

### Enhanced Dashboard

```bash
# Generate comprehensive dashboard (recommended)
python -m src.bidding_decision.stats.comparison --algorithm enhanced_facebook_prophet --enhanced-viz

# Dashboard with custom threshold and output
python -m src.bidding_decision.stats.comparison --algorithm ensemble --enhanced-viz --threshold 2.5 --viz-output dashboard.png
```

### Simple Table Visualization

```bash
# Generate clean table view
python -m src.bidding_decision.stats.comparison --algorithm enhanced_neural_prophet --simple-table

# Table with token ID display
python -m src.bidding_decision.stats.comparison --algorithm facebook_prophet --simple-table --show-tokens
```

## ⚙️ Algorithm-Specific Parameters

### Facebook Prophet Parameters

```bash
# Adjust changepoint sensitivity (0.001-0.5, default: 0.05)
python -m src.bidding_decision.stats.comparison --algorithm facebook_prophet --changepoint-prior 0.1

# Adjust seasonality strength (1-50, default: 10.0)
python -m src.bidding_decision.stats.comparison --algorithm facebook_prophet --seasonality-prior 20.0

# Combined custom parameters
python -m src.bidding_decision.stats.comparison --algorithm facebook_prophet --changepoint-prior 0.08 --seasonality-prior 15.0
```

### Neural Prophet Parameters

```bash
# Adjust training epochs (10-200, default: 50)
python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --epochs 100

# Adjust learning rate (0.01-1.0, default: 0.15)
python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --learning-rate 0.05

# Combined neural optimization
python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --epochs 80 --learning-rate 0.1
```

### Ensemble Parameters

```bash
# Use fast mode for quicker ensemble predictions
python -m src.bidding_decision.stats.comparison --algorithm ensemble --fast-mode

# Ensemble with custom seed and threshold
python -m src.bidding_decision.stats.comparison --algorithm ensemble --random-seed 789 --threshold 1.5
```

### Time Context

```bash
# Specify custom prediction time context
python -m src.bidding_decision.stats.comparison --algorithm enhanced_timesfm --current-time "2025-06-09 16:00:00"

# Use with any algorithm
python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --current-time "2025-06-10 14:30:00"
```

## 📊 Complete Examples

### Production Analysis Example

```bash
# Comprehensive analysis with enhanced visualization
python -m src.bidding_decision.stats.comparison \
    --algorithm enhanced_facebook_prophet \
    --threshold 2.0 \
    --random-seed 42 \
    --enhanced-viz \
    --output results/analysis_20250609.csv \
    --viz-output results/dashboard_20250609.png
```

### Speed-Optimized Example

```bash
# Fast analysis for quick decisions
python -m src.bidding_decision.stats.comparison \
    --algorithm facebook_prophet \
    --changepoint-prior 0.05 \
    --threshold 1.0 \
    --visualize \
    --output quick_analysis.csv
```

### Ensemble Comparison Example

```bash
# Compare ensemble vs single algorithms
python -m src.bidding_decision.stats.comparison --algorithm ensemble --random-seed 42 --output ensemble_results.csv
python -m src.bidding_decision.stats.comparison --algorithm enhanced_facebook_prophet --random-seed 42 --output facebook_results.csv
python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --random-seed 42 --output neural_results.csv
```

## 📈 Output Example

```
Using prediction algorithm: enhanced_facebook_prophet
Current time: 2025-06-09 16:13:07-04:00
Week period: 2025-06-06 12:00:00-04:00 to 2025-06-13 12:00:00-04:00
Tweets posted so far: 81
Time remaining: 3 days, 19:46:52

Comparison Table:
           Range  Pred (%)  Mkt (%)  Bid (%)  Ask (%)  Spread (%)  Diff (%)  Opp (%)  Adj-Sp (%)  Adj-Full (2.0%)  Buy-Only (2.0%)  Sell-Only (2.0%)
        175–199     44.9     35.5     35.0     36.0        1.0      8.9      8.9        7.9             5.9             5.9             0.0
        200–224     32.1     28.0     27.5     28.5        1.0      3.6      3.6        2.6             0.6             0.6             0.0
        150–174     12.8     25.0     24.5     25.5        1.0    -12.7     12.7       11.7             9.7             0.0             9.7
        225–249      6.2      8.5      8.0      9.0        1.0     -2.8      2.8        1.8             0.0             0.0             0.0
        250–274      2.5      2.0      1.5      2.5        1.0      0.0      0.0        0.0             0.0             0.0             0.0
        275–299      1.1      1.0      0.5      1.5        1.0     -0.4      0.4        0.0             0.0             0.0             0.0
        300–324      0.3      0.0      0.0      0.5        0.5     -0.2      0.2        0.0             0.0             0.0             0.0
        325–349      0.1      0.0      0.0      0.5        0.5     -0.4      0.4        0.0             0.0             0.0             0.0
    350 or more      0.0      0.0      0.0      0.5        0.5     -0.5      0.5        0.0             0.0             0.0             0.0
  EXPECTED VALUE    188.5    185.2     N/A     N/A        N/A      3.3      3.3        3.3             1.3             1.3             0.0

Best Trading Opportunity:
Range: 175–199
Prediction: 44.9%
Market: 35.5%
Bid: 35.0%
Ask: 36.0%
Spread: 1.0%
Difference: 8.9%
Opportunity: 8.9%
Spread-Adjusted Opportunity: 7.9%
Fully-Adjusted Opportunity: 5.9%
Buy-Only Opportunity: 5.9%
Sell-Only Opportunity: 0.0%
Token ID: 0x1a2b3c4d...
Recommendation: BUY 175–199 at 36.0% (prediction: 44.9%)
Edge: 5.9% after spread and 2.0% threshold
```

## 📋 Understanding the Output

### Column Descriptions

- **Range**: The tweet count outcome range (e.g., "175–199 tweets")
- **Pred (%)**: Model's predicted probability for this range
- **Mkt (%)**: Market's implied probability (bid+ask)/2
- **Bid (%)**: Price you can sell at (guaranteed execution)
- **Ask (%)**: Price you can buy at (guaranteed execution)
- **Spread (%)**: Bid-Ask spread (market maker profit margin)
- **Diff (%)**: Prediction minus execution price (Pred - Ask for buys, Pred - Bid for sells)
- **Opp (%)**: Absolute difference (raw edge before costs)
- **Adj-Sp (%)**: Opportunity after subtracting spread
- **Adj-Full (X%)**: Opportunity after subtracting spread AND your threshold
- **Buy-Only (X%)**: Opportunities where prediction > ask (buy opportunities)
- **Sell-Only (X%)**: Opportunities where prediction < bid (sell opportunities)

### Trading Logic

1. **Buy Signal**: When Pred(%) > Ask(%) + Spread + Threshold
2. **Sell Signal**: When Pred(%) < Bid(%) - Threshold
3. **No Trade**: When opportunity is below your threshold after costs

## 🛠️ Command Reference

### Core Options

```bash
--algorithm ALGO           # Algorithm choice (see supported algorithms above)
--output PATH              # Save comparison table CSV
--threshold FLOAT          # Minimum opportunity % (0-100, default: 0.0)
--random-seed INT          # Random seed for reproducibility (default: 42)
--current-time DATETIME    # Custom prediction time (YYYY-MM-DD HH:MM:SS)
```

### Visualization Options

```bash
--visualize               # Generate standard charts
--enhanced-viz           # Generate comprehensive dashboard (recommended)
--simple-table           # Generate clean table visualization
--viz-output PATH        # Save visualization to specific file
```

### Market Data Options

```bash
--no-refresh             # Use cached market data (faster)
--show-tokens            # Display token IDs in console output
--silent                 # Suppress console table output
```

### Algorithm Parameters

```bash
# Facebook Prophet
--changepoint-prior FLOAT  # Trend flexibility (0.001-0.5, default: 0.05)
--seasonality-prior FLOAT  # Seasonality strength (1-50, default: 10.0)

# Neural Prophet
--epochs INT               # Training epochs (10-200, default: 50)
--learning-rate FLOAT      # Learning rate (0.01-1.0, default: 0.15)

# Ensemble
--fast-mode               # Use faster basic models instead of enhanced
```

## 🎯 Algorithm Selection Guide

### For Speed (< 30 seconds)

- `facebook_prophet`: Fastest, reliable baseline
- `neural_prophet --epochs 30`: Quick neural network
- `timesfm`: Foundation model, no training

### For Accuracy (30s - 2min)

- `enhanced_facebook_prophet`: Multi-Prophet ensemble
- `neural_prophet`: Full neural training
- `enhanced_timesfm`: Multi-configuration TimesFM

### For Maximum Performance (2-5min)

- `ensemble`: All models combined
- `enhanced_neural_prophet`: Multi-neural ensemble

### For Testing/Development

- `prophet`: Legacy compatibility
- Any algorithm with `--random-seed 42`: Reproducible results

## 🔧 Advanced Usage

### Batch Analysis

```bash
# Run multiple algorithms with same seed
for algo in facebook_prophet neural_prophet timesfm; do
    python -m src.bidding_decision.stats.comparison \
        --algorithm $algo \
        --random-seed 42 \
        --threshold 2.0 \
        --output "results/${algo}_analysis.csv"
done
```

### Performance Comparison

```bash
# Compare enhanced vs standard versions
python -m src.bidding_decision.stats.comparison --algorithm facebook_prophet --random-seed 42 --output standard_fb.csv
python -m src.bidding_decision.stats.comparison --algorithm enhanced_facebook_prophet --random-seed 42 --output enhanced_fb.csv
```

### Production Monitoring

```bash
# Automated daily analysis
python -m src.bidding_decision.stats.comparison \
    --algorithm ensemble \
    --threshold 1.5 \
    --enhanced-viz \
    --output "daily_reports/$(date +%Y%m%d)_analysis.csv" \
    --viz-output "daily_reports/$(date +%Y%m%d)_dashboard.png"
```

## 📚 Output Files

By default, the tool saves files to:

- **CSV files**: `src/bidding_decision/stats/output/comparison_{algorithm}_{timestamp}.csv`
- **Visualizations**: `src/bidding_decision/stats/output/viz/comparison_{algorithm}_{timestamp}.png`
- **Table views**: `src/bidding_decision/stats/output/viz/table_{algorithm}_{timestamp}.png`

## 🔗 Python API

```python
from src.bidding_decision.stats.comparison import generate_comparison_table, enhanced_visualization

# Generate analysis with specific algorithm
df = generate_comparison_table(
    algorithm='enhanced_facebook_prophet',
    threshold=2.0,
    random_seed=42,
    changepoint_prior=0.08,
    seasonality_prior=15.0,
    output_path='analysis.csv'
)

# Create enhanced dashboard
enhanced_visualization(
    comparison_df=df,
    threshold=2.0,
    output_path='dashboard.png'
)
```

## 🚀 Performance Tips

1. **Use `facebook_prophet`** for quick analysis (8-10 seconds)
2. **Use `enhanced_facebook_prophet`** for production (45 seconds, much better accuracy)
3. **Use `ensemble --fast-mode`** for balanced speed/accuracy (2 minutes)
4. **Always set `--random-seed`** for reproducible results
5. **Use `--threshold 1.5`** or higher for realistic trading opportunities
6. **Use `--enhanced-viz`** for comprehensive analysis dashboards

## 🐛 Troubleshooting

### Algorithm Issues

- If enhanced algorithms fail, they automatically fall back to standard versions
- Use `--random-seed` for consistent debugging
- Check logs for specific model errors

### Data Issues

- Use `--no-refresh` if market data fetch fails
- Verify network connection for live Polymarket data
- Check timestamp format for `--current-time`

### Performance Issues

- Use `--fast-mode` for ensemble predictions
- Reduce `--epochs` for neural_prophet
- Use standard algorithms instead of enhanced variants for speed
