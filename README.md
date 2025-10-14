# Polymarket Algorithmic Trading System

A comprehensive suite of tools for fetching tweet data, making predictions, analyzing Polymarket events, and executing automated trading strategies.

## Overview

This system is designed to:

1. Automatically fetch Elon Musk's tweets
2. Analyze tweeting patterns and make predictions
3. Compare predictions with Polymarket odds
4. Identify statistical opportunities
5. Execute automated bidding strategies
6. Manage positions based on statistical advantages

## Quick Start

```bash
# Clone the repository
git clone https://github.com/konstantine25b/polymarket_algo.git
cd polymarket_algo

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your .env file with required API keys and wallet information
cp .env.example .env
# Edit .env with your actual credentials

# Run the automated scheduler with reasonable defaults when 2-6 days remain in the market
python3 -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --buy-threshold 1.0 --sell-threshold 0.5 --sell-below 3.0 --min-prediction 8.0 --weighted-selection --tweet-interval 110 --buy-interval 60 --sell-interval 5 --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --show-eachalgo-distribution --dry-run


python3 -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --buy-threshold 1.0 --sell-threshold 0.5 --sell-below 3.0 --min-prediction 8.0 --weighted-selection --tweet-interval 110 --buy-interval 60 --sell-interval 5 --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --show-eachalgo-distribution --timesfm-weight 0.40 --basic-prophet-weight 0.40 --neural-prophet-weight 0.085 --facebook-prophet-weight 0.085 --dry-run
# Option explanations:
# --algorithm ensemble         : Use ensemble method combining all prediction algorithms for maximum accuracy
# --random-seed 42             : Set random seed for reproducible predictions and consistent trading decisions
# --buy-threshold 1.5          : Only bid on opportunities with at least 1.5% edge over market price
# --sell-threshold 0.5         : Sell positions with at least 0.5% sell opportunity
# --sell-below 2.0             : Automatically sell positions with predictions below 2%
# --min-prediction 7.0         : Only bid on opportunities where our model predicts at least 7% probability
# --weighted-selection         : Use weighted probability selection instead of always choosing the best opportunity
# --tweet-interval 110         : Check for new tweets every 110 minutes
# --buy-interval 60            : Run auto-bidder every 60 minutes
# --sell-interval 10           : Run auto-seller every 10 minutes
# --use-csv-getter             : Use XTracker.io CSV method for tweet fetching instead of Apify
# --get-tweet-count-first      : Check tweet count from Polymarket before fetching to avoid unnecessary fetching
# --show-positions             : Display all your current positions when running
# --show-active-positions      : Display only positions for the active market week
# --dry-run                    : Test without placing actual orders (remove this for real trading)


# for simulation:

python -m src.scheduler.scheduler --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate pirvelad --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0


python -m src.terminal_logger.logger -n simulation_1 "python -m src.scheduler.scheduler --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate pirvelad_1 --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0"

# Run the automated scheduler with reasonable defaults when 1-2 days remain in the market
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --buy-threshold 1.5 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 9.0 --weighted-selection --interval 60 --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --dry-run
# Key differences:
# --algorithm enhanced_facebook_prophet : Use enhanced Facebook Prophet for faster execution than ensemble
# --min-prediction 9.0                  : Higher threshold (9% vs 7%) as less time remains in the market

# Run the automated scheduler with reasonable defaults when 6-7 days remain in the market
python -m src.scheduler.scheduler --algorithm facebook_prophet --random-seed 42 --buy-threshold 1.5 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 15.0 --weighted-selection --interval 60 --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --dry-run
# Key differences:
# --algorithm facebook_prophet : Use standard Facebook Prophet for fast execution when many days remain
# --min-prediction 15.0        : Much higher threshold (15%) when almost the entire week remains
```

## 🤖 Prediction Algorithms

The system now supports multiple advanced prediction algorithms for enhanced trading decisions:

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

# Use Enhanced Facebook Prophet with individual algorithm analysis
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --show-eachalgo-distribution

# Use Ensemble for maximum accuracy (slower but best results)
python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --interval 60

# Use Ensemble with individual algorithm analysis
python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --interval 60 --show-eachalgo-distribution

# For detailed algorithm analysis, run Enhanced Facebook Prophet directly:
python -m src.prediction_algos.facebook_prophet.enhanced_main --random-seed 42 --show-eachalgo-distribution

# For detailed algorithm analysis, run Ensemble directly:
python -m src.prediction_algos.ensemble.main --random-seed 42 --show-eachalgo-distribution

# Use Neural Prophet for complex pattern detection
python -m src.scheduler.scheduler --algorithm neural_prophet --random-seed 42

# Use TimesFM for fast, accurate predictions
python -m src.scheduler.scheduler --algorithm timesfm --random-seed 42
```

### 🔄 Reproducible Trading

All algorithms support reproducible results through random seed control:

```bash
# Same seed = Same predictions = Same trading decisions
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42

# Different seeds for testing algorithm stability
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 123
```

This ensures that:

- **Backtesting** produces consistent results
- **Algorithm comparison** is fair and reproducible
- **Trading strategies** can be reliably tested and deployed
- **Debug sessions** can replicate exact trading scenarios

## Directory Structure

### `/src/` - Main Source Code

#### `/src/apify/` - Tweet Fetching

Contains code for fetching Elon Musk's tweets using the Apify API.

- Efficiently retrieves tweets with incremental fetching
- Stores tweets in a database for analysis
- Handles rate limiting and connection issues

```bash
# Fetch latest tweets and add to database
python -m src.apify.get_elon_tweets --max-tweets 40 --use-client --add-to-db
```

#### `/src/formating_tweet_data/` - Data Processing

Tools for cleaning and formatting tweet data for analysis.

- Normalizes date formats
- Groups tweets by day for trend analysis
- Prepares data for prediction algorithms

#### `/src/algos/` - Prediction Algorithms

Various algorithms for predicting Elon's tweeting patterns.

- Time series analysis
- Pattern recognition
- Historical trend modeling

#### `/src/polymarket/` - Polymarket API Integration

Tools for interacting with Polymarket's API and analyzing markets.

- Fetches market data and order books
- Analyzes liquidity and price movements
- Provides wallet balance information
- Execution of buy and sell orders

```bash
# Fetch and visualize market data
python -m src.polymarket.main --generate-plot

# Scan for markets with rewards
python -m src.polymarket.market_scanner --rewarded

# Get prices for specific tokens using order book
python -m src.polymarket.order_book.get_prices

# Get prices for all active markets (shows token ID, question, BUY/SELL prices)
python -m src.polymarket.order_book.get_prices

# Get price for a specific market by token ID
python -m src.polymarket.order_book.get_price 47979392807610373586249777498703710597487450905720498331079563053270702791739

# Use in code:
from src.polymarket.order_book import get_prices, get_price

# Get all markets with prices and questions
all_markets = get_prices()
# Returns: {"token_id": {"question": "Market question", "market_id": "100–124  May 23–30?", "BUY": 0.123, "SELL": 0.456}}

# Get specific market by token ID
market_data = get_price("47979392807610373586249777498703710597487450905720498331079563053270702791739")
# Returns: {"question": "Will Elon tweet 100–124 times May 23–30?", "market_id": "100–124  May 23–30?", "BUY": 0.093, "SELL": 0.105}
```

#### `/src/polymarket_predictor/` - Prediction Integration

Integrates tweet predictions with Polymarket markets.

- Generates probabilities for tweet count ranges
- Compares predictions with market prices
- Outputs expected values and statistical edges

```bash
# Run prediction with default settings
python -m src.polymarket_predictor
```

#### `/src/bidding_decision/` - Trading Logic

Contains tools for making bidding decisions and executing trades.

- Auto-Bidder for identifying and placing buy orders
- Position Seller for identifying and executing sell orders
- Statistical analysis for identifying opportunities

```bash
# Run the auto-bidder in dry-run mode
python -m src.bidding_decision.auto_bid.run --algorithm enhanced_facebook_prophet --random-seed 42 --threshold 2.0 --min-prediction 10.0 --dry-run

# Run the position seller to identify positions to sell
python -m src.bidding_decision.auto_bid.run_seller --algorithm enhanced_facebook_prophet --random-seed 42 --sell-below 5.0 --auto-sell --dry-run
```

#### `/src/scheduler/` - Automated Workflow

Scheduler for automating the entire workflow from fetching tweets to placing orders.

- Configurable intervals for periodic execution
- Options for tweet fetching, prediction, and trading
- Balance checking and trade execution

```bash
# Run scheduler with optimized settings
python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --tweet-interval 20 --buy-interval 60 --sell-interval 10 --buy-threshold 1.5 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 7.0 --weighted-selection --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --dry-run
```

This configuration uses an optimized approach:

- Every 20 minutes: Check tweet counts without forcing fetching
- Every 60 minutes: Check tweet counts, fetch if needed, then run auto-bidder
- Every 10 minutes: Check tweet counts, fetch if needed, then run auto-seller

This minimizes unnecessary API calls while ensuring all trading decisions are made with up-to-date data.

#### Individual Algorithm Analysis

For enhanced debugging and model understanding, both Enhanced Facebook Prophet and Ensemble algorithms support showing individual algorithm probability distributions:

```bash
# Show individual algorithm distributions with Enhanced Facebook Prophet
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --show-eachalgo-distribution --dry-run

# Show individual algorithm distributions with Ensemble
python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --show-eachalgo-distribution --dry-run

# Run directly for detailed analysis
python -m src.prediction_algos.facebook_prophet.enhanced_main --random-seed 42 --show-eachalgo-distribution
python -m src.prediction_algos.ensemble.main --random-seed 42 --show-eachalgo-distribution
```

This feature displays:

- **Enhanced Facebook Prophet**: Shows distributions for Daily Prophet, Hourly Prophet, Conservative Prophet, Aggressive Prophet, Weekly Prophet, Pattern-based, and Random Forest models
- **Ensemble**: Shows distributions for Neural Prophet, Facebook Prophet, TimesFM, and Basic Prophet models
- **All probability categories**: Displays probabilities for all tweet count ranges, not just the top ones
- **Model weights**: Shows how much each algorithm contributes to the final prediction

Perfect for understanding which models are conservative vs aggressive and how they contribute to the final ensemble prediction.

#### `/src/terminal_logger/` - Terminal Output Logging

Simple utility for logging terminal output to files when running commands.

- Saves terminal output to timestamped log files
- Works with any command, including those with emojis and special characters
- Supports custom log filenames

```bash
# Run any command and log its output
python -m src.terminal_logger.logger "your command here"

# Run the scheduler with logging
python -m src.terminal_logger.logger "python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --buy-threshold 1.5 --dry-run"

# Run with custom log filename
python -m src.terminal_logger.logit --logfile my_custom_log.log python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --dry-run
```

See the [Terminal Logger README](src/terminal_logger/README.md) for more details.

### Key Configuration Files

- `requirements.txt` - Python dependencies
- `.env` - Environment variables for API keys and wallet information

## Core Functionality

### 1. Automated Tweet Collection

The system automatically fetches Elon Musk's tweets at regular intervals, storing them in a database for analysis. Advanced incremental fetching ensures continuous data without gaps.

### 2. Prediction Algorithms

Multiple algorithms analyze historical tweet patterns to predict future tweeting behavior, with particular focus on weekly tweet counts relevant to Polymarket events.

### 3. Statistical Market Analysis

The system compares prediction models with Polymarket odds to identify statistical edges where the market price differs from the model's prediction.

### 4. Automated Trading

Based on statistical analysis, the system can:

- Place buy orders for outcomes with positive expected value
- Manage existing positions
- Sell positions when statistically advantageous or when predictions indicate low probability

### 5. Position Management

The Position Seller automatically identifies positions that should be sold based on:

- Statistical opportunities (when market price exceeds model prediction)
- Low prediction percentage (automatically exits positions with low win probability)

### 6. Robust Tweet Count Mismatch Handling

The system now includes enhanced tweet count verification and recovery mechanisms:

- Compares tweet counts between Polymarket and local database
- When mismatches are detected, automatically re-fetches tweets up to 3 times to resolve the discrepancy
- If mismatches persist after 3 retries, falls back to Apify's API as a reliable alternative
- Continuously verifies counts after each attempt to ensure data integrity
- Provides detailed logging and console output about the reconciliation process
- Continues with prediction and trading operations even if counts can't be perfectly reconciled

This multi-stage approach ensures maximum data reliability and reduces the chance of acting on incomplete information.

```bash
# Example command using the enhanced tweet count verification
python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --get-tweet-count-first --use-csv-getter --interval 60 --dry-run
```

## Detailed Configuration Options

### Scheduler Options

The scheduler is the main entry point for the automated system. Key options include:

```
--interval MINUTES     Global interval for all operations (default: 20)
--tweet-interval MINUTES Interval between tweet fetching runs (overrides global interval)
--buy-interval MINUTES  Interval between auto-bidder runs (overrides global interval)
--sell-interval MINUTES Interval between auto-seller runs (overrides global interval)
--buy-threshold FLOAT  Minimum edge required to place buy orders (default: 0.0)
--sell-threshold FLOAT Minimum edge required to place sell orders (default: 0.0)
--sell-below FLOAT     Automatically sell positions with prediction below this percentage
--min-prediction FLOAT Only bid on opportunities with prediction at or above this value
--amount FLOAT         Amount to bid in USDC (default: 1.0)
--dry-run              Test without placing actual orders
--weighted-selection   Use weighted probability selection instead of always choosing the best opportunity
--show-positions       Show all current positions when running
--show-active-positions Show positions for active market when running
--show-eachalgo-distribution Show individual algorithm probability distributions (enhanced_facebook_prophet and ensemble only)
```

### Example with Different Intervals

Run the scheduler with different intervals for each operation:

```bash
# Run tweet count checks every 20 minutes, buying every 60 minutes, and selling every 10 minutes
python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --tweet-interval 20 --buy-interval 60 --sell-interval 10 --buy-threshold 1.5 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 7.0 --weighted-selection --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --dry-run
```

### Auto-Bidder Options

The Auto-Bidder identifies and places buy orders. Key options include:

```
--algorithm ALGO       Choose prediction algorithm (prophet, facebook_prophet, enhanced_facebook_prophet, neural_prophet, enhanced_neural_prophet, timesfm, enhanced_timesfm, ensemble)
--random-seed INT      Random seed for reproducible predictions (default: 42)
--threshold FLOAT      Minimum statistical edge required (default: 0.0)
--min-prediction FLOAT Only consider opportunities with prediction above this value
--amount FLOAT         Amount to bid in USDC (default: 1.0)
--weighted-selection   Use weighted selection instead of always choosing the best opportunity
--dry-run              Find opportunities but don't place actual orders
```

### Position Seller Options

The Position Seller identifies and sells positions. Key options include:

```
--algorithm ALGO       Choose prediction algorithm (prophet, facebook_prophet, enhanced_facebook_prophet, neural_prophet, enhanced_neural_prophet, timesfm, enhanced_timesfm, ensemble)
--random-seed INT      Random seed for reproducible predictions (default: 42)
--threshold FLOAT      Minimum statistical edge required for selling (default: 0.0)
--sell-below FLOAT     Sell positions with prediction below this percentage
--auto-sell            Automatically execute sell orders (otherwise just show recommendations)
--dry-run              Show what would be sold without executing actual orders
```

## Running in Production

For running in production as a background service:

```bash
# Run as a background service with Enhanced Facebook Prophet
nohup python -m src.scheduler.scheduler --algorithm enhanced_facebook_prophet --random-seed 42 --buy-threshold 1.0 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 5.0 --weighted-selection --interval 30 > /dev/null 2>&1 &

# Run as a background service with Ensemble for maximum accuracy
nohup python -m src.scheduler.scheduler --algorithm ensemble --random-seed 42 --buy-threshold 1.5 --sell-threshold 0.8 --sell-below 3.0 --min-prediction 8.0 --weighted-selection --interval 60 > /dev/null 2>&1 &

# Find the process ID
ps aux | grep scheduler

# Stop the service
kill <process_id>
```

## Requirements

- Python 3.8+
- Access to the Apify API for tweet fetching
- Ethereum wallet with MATIC and USDC for Polymarket trading
- Prophet and other statistical packages for prediction

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
