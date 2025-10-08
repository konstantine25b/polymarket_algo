# Tweet Scheduler

A tool for automating the tweet fetching, prediction processes, and automated trading for Polymarket.

## Overview

This module provides an automated scheduler that periodically:

1. Fetches Elon Musk's tweets and stores them in the database
2. Runs the Polymarket predictor to update predictions
3. Runs the Auto-Bidder to place orders based on identified trading opportunities
4. Runs the Position Seller to automatically sell positions that should be sold

## Features

- **Configurable interval**: Set how often to run the process (default: 20 minutes)
- **Multiple prediction algorithms**: Choose from Facebook Prophet, Neural Prophet, TimesFM, Enhanced variants, and Ensemble methods
- **Reproducible predictions**: Random seed control for consistent trading decisions
- **Selective execution**: Run only tweet fetching or only predictions
- **Smart incremental fetching**: Uses advanced incremental fetching strategy by default to ensure continuous tweet collection
- **Alternative data sources**: Option to use either Apify (default) or TweetCSVGetter (XTracker.io) for fetching tweets
- **Pre-fetch validation**: Option to check tweet count from Polymarket before fetching tweets
- **Count verification**: Compares local database count with Polymarket's website count
- **Retry mechanism**: Configurable retries when getting tweet count from Polymarket
- **Logging**: Comprehensive logging to file and console
- **One-time execution**: Option to run once and exit
- **Quiet mode**: Reduce output verbosity
- **Automated trading**: Automatically places buy orders and sells positions on Polymarket based on prediction data
- **Trading opportunities**: Identifies potential trading opportunities with customizable thresholds
- **Minimum prediction filtering**: Only bid on opportunities with predictions above a specified percentage
- **Weighted selection**: Option to use weighted probability selection for buy opportunities instead of always choosing the best one
- **Separate thresholds**: Configure different thresholds for buying and selling positions
- **Dry run mode**: Test the auto-bidder and auto-seller without placing actual orders
- **Configurable bid amount**: Set the amount of USDC to use for each bid
- **Statistical analysis**: View detailed stats on each market opportunity
- **Balance checking**: Automatically checks wallet balance before placing buy orders, skipping if insufficient funds
- **Conditional bidding**: Only runs auto-bidder if there's enough USDC balance (configurable minimum threshold)
- **Tweet verification**: Shows the total and daily tweet counts after fetching and validates against Polymarket's website
- **Auto-sell low probability positions**: Automatically sells positions where your model's prediction is below a specified threshold

## 🤖 Prediction Algorithms

The scheduler now supports multiple prediction algorithms for enhanced trading decisions:

### Available Algorithms

| Algorithm                   | Description               | Speed | Accuracy  | Best Use Case         |
| --------------------------- | ------------------------- | ----- | --------- | --------------------- |
| `prophet`                   | Legacy predictor          | ~5s   | Good      | Baseline (default)    |
| `facebook_prophet`          | Standard Facebook Prophet | ~8s   | Very Good | General forecasting   |
| `enhanced_facebook_prophet` | Multi-Prophet ensemble    | ~45s  | Superior  | **Recommended**       |
| `neural_prophet`            | Deep learning predictor   | ~30s  | Excellent | Complex patterns      |
| `enhanced_neural_prophet`   | Multi-Neural ensemble     | ~3min | Superior  | High accuracy trading |
| `timesfm`                   | Google foundation model   | ~20s  | Excellent | Zero-shot learning    |
| `enhanced_timesfm`          | Multi-TimesFM ensemble    | ~2min | Superior  | Advanced trading      |
| `ensemble`                  | All models combined       | ~3min | Maximum   | Best overall accuracy |

### Algorithm Selection Examples

```bash
# Use Enhanced Facebook Prophet (recommended for most cases)
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42

# Use Ensemble for maximum accuracy (slower but best results)
python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --interval 60

# Use Neural Prophet for complex pattern detection
python -m src.scheduler.scheduler --algorithm neural_prophet --random-seed 42

# Use TimesFM for fast, accurate predictions
python -m src.scheduler.scheduler --algorithm timesfm --random-seed 42
```

## Command-Line Usage

```bash
# Activate virtual environment
source venv/bin/activate

# I use it commonly - this setup provides a balanced automated trading approach:
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --buy-threshold 1.0 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 5.0 --weighted-selection --interval 30
# In this command:
# --algorithm enhanced_facebook_prophet: Use the enhanced Facebook Prophet algorithm for better accuracy
# --random-seed 42: Ensure reproducible predictions across runs
# --buy-threshold 1.0: Only bid on opportunities with at least 1% edge over market price
# --sell-threshold 0.5: Sell positions with at least 0.5% sell opportunity
# --sell-below 2.0: Automatically sell positions with predictions below 2%
# --min-prediction 5.0: Only bid on opportunities where our model predicts at least 5% probability
# --weighted-selection: Use weighted probability selection instead of always choosing the best opportunity
# --interval 30: Run the scheduler every 30 minutes

# For maximum accuracy trading (slower but best results)
python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --buy-threshold 2.0 --sell-threshold 1.0 --sell-below 3.0 --min-prediction 8.0 --weighted-selection --interval 60

# For testing (same settings but in dry run mode - no real orders placed)
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --buy-threshold 1.0 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 5.0 --weighted-selection --interval 30 --dry-run

# For fast, frequent trading with Neural Prophet
python -m src.scheduler.scheduler --algorithm neural_prophet --random-seed 42 --buy-threshold 1.5 --sell-threshold 0.8 --min-prediction 6.0 --interval 20

# Run with only buy opportunities shown but no actual buying (sell orders still execute)
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --buy-threshold 1.0 --sell-threshold 0.5 --min-prediction 5.0 --no-buy

# Run with only sell opportunities shown but no actual selling (buy orders still execute)
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --buy-threshold 1.0 --sell-threshold 0.5 --min-prediction 5.0 --no-sell

# Show both buy and sell opportunities without executing any orders
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --buy-threshold 1.0 --sell-threshold 0.5 --min-prediction 5.0 --no-buy --no-sell

# Run with default settings (every 20 minutes)
python -m src.scheduler.scheduler

# Run with custom interval (every 5 minutes)
python -m src.scheduler.scheduler --interval 5

# Only fetch tweets, don't run predictions or trading
python -m src.scheduler.scheduler --tweets-only

# Only run predictions and trading, don't fetch tweets
python -m src.scheduler.scheduler --predictions-only

# Run jobs once and exit (don't keep running)
python -m src.scheduler.scheduler --run-once

# Change the maximum number of tweets to fetch
python -m src.scheduler.scheduler --max-tweets 100

# Disable debug mode for tweet fetching
python -m src.scheduler.scheduler --no-debug

# Run in quiet mode with less output
python -m src.scheduler.scheduler --quiet

# Use TweetCSVGetter (XTracker.io) instead of Apify for tweet fetching
python -m src.scheduler.scheduler --use-csv-getter

# Get tweet count before fetching and verify with database after fetching
python -m src.scheduler.scheduler --get-tweet-count-first

# Set maximum retries for tweet count retrieval
python -m src.scheduler.scheduler --max-count-retries 5

# Combined approach with tweet count checking and CSV getter
python -m src.scheduler.scheduler --use-csv-getter --get-tweet-count-first

# Customize incremental fetching parameters
python -m src.scheduler.scheduler --initial-batch 60 --max-batch 300

# Disable incremental fetching (not recommended)
python -m src.scheduler.scheduler --no-incremental

# Don't run the auto-bidder after predictions
python -m src.scheduler.scheduler --no-bidding

# Don't run the auto-seller after predictions
python -m src.scheduler.scheduler --no-selling

# Set minimum thresholds for buying and selling (e.g., 3% for buying, 2% for selling)
python -m src.scheduler.scheduler --buy-threshold 3.0 --sell-threshold 2.0

# Only bid on opportunities with predictions of at least 10%
python -m src.scheduler.scheduler --min-prediction 10.0

# Set the bid amount to 2.5 USDC
python -m src.scheduler.scheduler --amount 2.5

# Use weighted selection for buy opportunities
python -m src.scheduler.scheduler --weighted-selection

# Run in dry run mode (don't place real orders)
python -m src.scheduler.scheduler --dry-run

# Don't display the full statistics table
python -m src.scheduler.scheduler --no-stats

# Set the minimum USDC balance required for bidding
python -m src.scheduler.scheduler --min-usdc 2.0

# Skip balance checking (always attempt to place buy orders)
python -m src.scheduler.scheduler --skip-balance-check

# Skip tweet count verification after fetching
python -m src.scheduler.scheduler --no-tweet-verify

# Automatically sell positions with prediction below 5%
python -m src.scheduler.scheduler --sell-below 5.0

# Show detailed debugging information for the position seller
python -m src.scheduler.scheduler --debug-seller

# Combine multiple options with advanced algorithm
python -m src.scheduler.scheduler --algorithm enhanced_neural_prophet --random-seed 42 --interval 15 --max-tweets 50 --quiet --buy-threshold 3.0 --sell-threshold 2.0 --amount 2.0 --weighted-selection --dry-run --min-usdc 1.5 --sell-below 3.0 --get-tweet-count-first
```

## 🎯 Recommended Trading Configurations

### Conservative Trading (Recommended for beginners)

```bash
python -m src.scheduler.scheduler \
  --algorithm facebook_prophet \
  --random-seed 42 \
  --buy-threshold 2.0 \
  --sell-threshold 1.0 \
  --sell-below 3.0 \
  --min-prediction 8.0 \
  --amount 1.0 \
  --interval 30 \
  --dry-run  # Remove when ready for real trading
```

### Balanced Trading (Good for most users)

```bash
python -m src.scheduler.scheduler \
  --algorithm enhanced_facebook_prophet \
  --random-seed 42 \
  --buy-threshold 1.5 \
  --sell-threshold 0.8 \
  --sell-below 2.5 \
  --min-prediction 6.0 \
  --weighted-selection \
  --amount 1.5 \
  --interval 25
```

### Aggressive Trading (For experienced traders)

```bash
python -m src.scheduler.scheduler \
  --algorithm ensemble \
  --random-seed 42 \
  --buy-threshold 1.0 \
  --sell-threshold 0.5 \
  --sell-below 2.0 \
  --min-prediction 4.0 \
  --weighted-selection \
  --amount 2.0 \
  --interval 20
```

### Maximum Accuracy (Slower but best results)

```bash
python -m src.scheduler.scheduler \
  --algorithm ensemble \
  --random-seed 42 \
  --buy-threshold 2.5 \
  --sell-threshold 1.2 \
  --sell-below 4.0 \
  --min-prediction 10.0 \
  --amount 3.0 \
  --interval 60
```

## Command-Line Options

### General Options

- `--interval`: Set the global interval between runs in minutes (default: 20)
- `--tweet-interval`: Set the interval between tweet fetching runs in minutes (overrides global interval)
- `--buy-interval`: Set the interval between auto-bidder runs in minutes (overrides global interval)
- `--sell-interval`: Set the interval between auto-seller runs in minutes (overrides global interval)
- `--tweets-only`: Only run the tweet fetching job
- `--predictions-only`: Only run the prediction and trading jobs
- `--max-tweets`: Maximum number of tweets to fetch (default: 40)
- `--no-debug`: Disable debug mode for tweet fetching
- `--run-once`: Run jobs once and exit
- `--quiet`: Reduce output verbosity

### Algorithm & Prediction Options

- `--algorithm`: Prediction algorithm to use (default: prophet)
  - Choices: `prophet`, `facebook_prophet`, `enhanced_facebook_prophet`, `neural_prophet`, `enhanced_neural_prophet`, `timesfm`, `enhanced_timesfm`, `ensemble`
- `--random-seed`: Random seed for reproducible predictions (default: 42)
- `--no-prophet`: Disable Prophet algorithm for predictions (use standard algorithm instead)

### Data Source Options

- `--use-csv-getter`: Use TweetCSVGetter (XTracker.io) instead of Apify for tweet fetching
- `--get-tweet-count-first`: Get tweet count from Polymarket before fetching tweets and verify with database
- `--max-count-retries`: Maximum number of retries for tweet count retrieval (default: 3)
- `--no-incremental`: Disable incremental fetching (not recommended)
- `--initial-batch`: Initial batch size for incremental fetching (default: 40)
- `--max-batch`: Maximum batch size for incremental fetching (default: 200)
- `--no-tweet-verify`: Skip verifying and displaying tweet counts after fetching

### Trading Control Options

- `--no-bidding`: Don't run the auto-bidder after predictions
- `--no-selling`: Don't run the auto-seller after predictions
- `--no-buy`: Run auto-bidder but don't execute buy orders (show opportunities only)
- `--no-sell`: Run auto-seller but don't execute sell orders (show opportunities only)
- `--dry-run`: Run auto-bidder and auto-seller in dry run mode (don't place real orders)

### Trading Threshold Options

- `--buy-threshold`: Minimum opportunity percentage for placing buy orders (default: 0.0)
- `--sell-threshold`: Minimum opportunity percentage for selling positions (default: 0.0)
- `--min-prediction`: Only bid on opportunities with prediction percentage at or above this value (default: 0.0)
- `--sell-below`: Automatically sell positions with prediction below this percentage (default: 0.0)

### Trading Execution Options

- `--amount`: Amount to bid in USDC (default: 1.0)
- `--weighted-selection`: Use weighted probability selection for buy opportunities instead of always choosing the best opportunity
- `--min-usdc`: Minimum USDC balance required to run auto-bidder (default: 1.0)
- `--skip-balance-check`: Skip checking wallet balance before running auto-bidder

### Display Options

- `--no-stats`: Don't display the full statistics table with market opportunities
- `--debug-seller`: Show detailed debugging information for the position seller
- `--show-positions`: Show all current positions when running
- `--show-active-positions`: Show positions for active market when running

### Simulation Options

- `--simulate RUN_NAME`: Run in simulation mode using the specified simulation run name
- `--strategy STRATEGY`: Strategy to use for simulation (default: strategy_1)
- `--sim-balance FLOAT`: Initial balance for new simulation runs (default: $1000.0)

## Command-Line Examples

```bash
# Show all positions and active market positions when running
python -m src.scheduler.scheduler --show-positions --show-active-positions
# --show-positions         : Display all your current positions across all markets
# --show-active-positions  : Display only positions for the active market week

# Only show active market positions, not all positions
python -m src.scheduler.scheduler --show-active-positions
# --show-active-positions  : Display only positions for the active market week (May 16-23, etc.)

# Test different algorithms with same random seed for comparison
python -m src.scheduler.scheduler --algorithm facebook_prophet --random-seed 123 --dry-run --run-once
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 123 --dry-run --run-once
python -m src.scheduler.scheduler --algorithm neural_prophet --random-seed 123 --dry-run --run-once

# Use Enhanced TimesFM for advanced trading with reproducible results
python -m src.scheduler.scheduler --algorithm enhanced_timesfm --random-seed 42 --buy-threshold 1.8 --sell-threshold 0.9 --weighted-selection

# Run Ensemble algorithm for maximum accuracy (best for important trading decisions)
python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --buy-threshold 2.5 --sell-threshold 1.5 --min-prediction 8.0 --interval 45
```

## Simulation Mode

The scheduler includes a comprehensive simulation mode that allows you to test trading strategies without using real money. The simulation uses the same prediction algorithms and bidding strategies as the real trading system, but operates on virtual funds and simulated positions.

### Quick Start with Simulation

```bash
# Basic simulation run with default settings
python -m src.scheduler.scheduler --simulate my_test_run --run-once --dry-run

# Advanced simulation with custom parameters
python -m src.scheduler.scheduler \
  --simulate advanced_test \
  --strategy strategy_1 \
  --sim-balance 1000 \
  --amount 50.0 \
  --buy-threshold 3.0 \
  --weighted-selection \
  --min-prediction 10.0 \
  --sell-threshold 2.0 \
  --sell-below 20.0 \
  --run-once

# Continuous simulation (runs every 20 minutes)
python -m src.scheduler.scheduler \
  --simulate continuous_test \
  --amount 25.0 \
  --buy-threshold 2.0 \
  --sell-threshold 1.0 \
  --weighted-selection
```

### Simulation Features

**Automatic Run Creation**: If the specified simulation run doesn't exist, it will be automatically created with:

- The specified initial balance (--sim-balance)
- Real Polymarket market data initialization
- Proper tracking of all simulation metrics

**Real Market Data**: Simulations use real, up-to-date Polymarket data including:

- Current market prices and spreads
- Real order book data (bid/ask prices)
- Live prediction data from your models

**Complete Position Tracking**:

- Tracks all buy/sell transactions
- Calculates profit/loss for each position
- Maintains balance and share inventories
- Provides detailed transaction history

**Strategy Integration**: Uses the same bidding strategies as real trading:

- Same opportunity identification algorithms
- Same weighted selection logic
- Same prediction filtering and thresholds

### Simulation Examples

```bash
# ese kaia

python -m src.scheduler.scheduler --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 2 --sell-interval 1 --simulate pirvelad --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0

# Conservative simulation - only bid on high-confidence opportunities
python -m src.scheduler.scheduler \
  --simulate conservative_strategy \
  --sim-balance 500 \
  --amount 20.0 \
  --buy-threshold 5.0 \
  --min-prediction 15.0 \
  --sell-threshold 3.0 \
  --sell-below 10.0 \
  --run-once

# Aggressive simulation - bid on more opportunities with larger amounts
python -m src.scheduler.scheduler \
  --simulate aggressive_strategy \
  --sim-balance 2000 \
  --amount 100.0 \
  --buy-threshold 1.0 \
  --min-prediction 5.0 \
  --weighted-selection \
  --sell-threshold 0.5 \
  --sell-below 25.0 \
  --run-once

# Testing simulation - see what would happen without making any trades
python -m src.scheduler.scheduler \
  --simulate testing_strategy \
  --amount 30.0 \
  --buy-threshold 2.0 \
  --min-prediction 8.0 \
  --dry-run \
  --run-once

# Long-running simulation - test strategy over time
python -m src.scheduler.scheduler \
  --simulate long_term_test \
  --sim-balance 1500 \
  --amount 40.0 \
  --buy-threshold 2.5 \
  --sell-threshold 1.5 \
  --weighted-selection \
  --interval 30
```

### Viewing Simulation Results

After running simulations, you can view detailed results using the simulation initialization tool:

```bash
# View simulation run information
python -m src.simulation.initialization --info my_test_run

# List all simulation runs
python -m src.simulation.initialization --list

# View specific position details
python -m src.simulation.bidding_decision.strategy_1 --analyze my_test_run
```

### Simulation vs Real Trading

| Feature        | Real Trading            | Simulation                           |
| -------------- | ----------------------- | ------------------------------------ |
| **Funds**      | Real USDC from wallet   | Virtual balance                      |
| **Markets**    | Real Polymarket orders  | Real market data, simulated orders   |
| **Strategies** | Live bidding algorithms | Same algorithms, simulated execution |
| **Risk**       | Real money at risk      | No financial risk                    |
| **Data**       | Real-time market data   | Same real-time data                  |
| **Results**    | Real profit/loss        | Simulated profit/loss tracking       |

### Best Practices for Simulation

1. **Start with small amounts**: Use realistic bid amounts that you would actually trade with
2. **Test different strategies**: Try conservative vs aggressive approaches
3. **Use realistic thresholds**: Don't set thresholds too low or you'll trade on everything
4. **Monitor over time**: Run continuous simulations to see how strategies perform over multiple market cycles
5. **Compare with dry-run**: Use `--dry-run` within simulation to see opportunities without taking them

Example workflow:

```bash
# 1. Test with dry-run to see opportunities
python -m src.scheduler.scheduler --simulate test1 --dry-run --run-once

# 2. Run actual simulation with conservative settings
python -m src.scheduler.scheduler --simulate test1 --buy-threshold 3.0 --run-once

# 3. Check results
python -m src.simulation.initialization --info test1

# 4. Continue simulation or adjust parameters
python -m src.scheduler.scheduler --simulate test1 --buy-threshold 2.0 --run-once
```

## 🔄 Reproducible Trading

The scheduler now supports reproducible trading decisions through random seed control:

```bash
# Same seed = Same predictions = Same trading decisions
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42

# Different seeds for testing algorithm stability
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 123
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 456
```

This ensures that:

- **Backtesting** produces consistent results
- **Algorithm comparison** is fair and reproducible
- **Trading strategies** can be reliably tested and deployed
- **Debug sessions** can replicate exact trading scenarios

## Tweet Count Verification

## 📊 Algorithm Performance Guidelines

### Speed vs Accuracy Trade-offs

**For frequent trading (every 15-30 minutes):**

- Use `facebook_prophet` or `neural_prophet`
- Fast execution, good accuracy

**For standard trading (every 30-60 minutes):**

- Use `enhanced_facebook_prophet` (recommended)
- Best balance of speed and accuracy

**For high-stakes trading (every 60+ minutes):**

- Use `ensemble` or `enhanced_neural_prophet`
- Maximum accuracy, worth the wait

### Random Seed Best Practices

```bash
# Production: Use a fixed seed for consistency
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42

# Testing: Use different seeds to verify algorithm stability
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 123 --dry-run
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 456 --dry-run
```

## 🛠️ Integration with Auto-Bidder and Auto-Seller

The algorithm selection automatically applies to both the Auto-Bidder and Auto-Seller components:

- **Auto-Bidder**: Uses the selected algorithm to identify buy opportunities
- **Auto-Seller**: Uses the same algorithm to evaluate existing positions for selling
- **Consistency**: Both components use the same random seed for consistent decision-making

This ensures that your entire trading strategy uses a unified prediction approach across all components.

## ⚠️ Important Notes

1. **Enhanced algorithms** generally provide better accuracy but take longer to run
2. **Random seeds** ensure reproducible results - use the same seed for consistent trading
3. **Algorithm choice** affects both buying and selling decisions automatically
4. **Ensemble method** provides the best accuracy but is slowest (use for important decisions)
5. **Always test** new algorithms with `--dry-run` before live trading

## 🔗 Related Components

- **Auto-Bidder**: `src/bidding_decision/auto_bid/` - Automated buy order placement
- **Auto-Seller**: `src/bidding_decision/auto_bid/run_seller.py` - Automated position selling
- **Comparison Tool**: `src/bidding_decision/stats/comparison.py` - Algorithm analysis and comparison
- **Prediction Algorithms**: `src/prediction_algos/` - Individual algorithm implementations
