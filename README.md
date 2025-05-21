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
python -m src.scheduler.scheduler --buy-threshold 1.5 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 7.0 --weighted-selection --interval 60 --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --dry-run
# Option explanations:
# --buy-threshold 1.5      : Only bid on opportunities with at least 1.5% edge over market price
# --sell-threshold 0.5     : Sell positions with at least 0.5% sell opportunity
# --sell-below 2.0         : Automatically sell positions with predictions below 2%
# --min-prediction 7.0     : Only bid on opportunities where our model predicts at least 7% probability
# --weighted-selection     : Use weighted probability selection instead of always choosing the best opportunity
# --interval 60            : Run the scheduler every 60 minutes
# --use-csv-getter         : Use XTracker.io CSV method for tweet fetching instead of Apify
# --get-tweet-count-first  : Check tweet count from Polymarket before fetching to avoid unnecessary fetching
# --show-positions         : Display all your current positions when running
# --show-active-positions  : Display only positions for the active market week
# --dry-run                : Test without placing actual orders (remove this for real trading)

# Run the automated scheduler with reasonable defaults when 1-2 days remain in the market
python -m src.scheduler.scheduler --buy-threshold 1.5 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 9.0 --weighted-selection --interval 60 --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --dry-run
# Key difference:
# --min-prediction 9.0     : Higher threshold (9% vs 7%) as less time remains in the market

# Run the automated scheduler with reasonable defaults when 6-7 days remain in the market
python -m src.scheduler.scheduler --buy-threshold 1.5 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 15.0 --weighted-selection --interval 60 --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --dry-run
# Key difference:
# --min-prediction 15.0    : Much higher threshold (15%) when almost the entire week remains
```

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
python -m src.bidding_decision.auto_bid.run --threshold 2.0 --min-prediction 10.0 --dry-run

# Run the position seller to identify positions to sell
python -m src.bidding_decision.auto_bid.run_seller --sell-below 5.0 --auto-sell --dry-run
```

#### `/src/scheduler/` - Automated Workflow

Scheduler for automating the entire workflow from fetching tweets to placing orders.

- Configurable intervals for periodic execution
- Options for tweet fetching, prediction, and trading
- Balance checking and trade execution

```bash
# Run scheduler with optimized settings
python -m src.scheduler.scheduler --buy-threshold 1.0 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 5.0 --weighted-selection --interval 30
```

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

## Detailed Configuration Options

### Scheduler Options

The scheduler is the main entry point for the automated system. Key options include:

```
--interval MINUTES     How often to run the process (default: 20)
--buy-threshold FLOAT  Minimum edge required to place buy orders (default: 0.0)
--sell-threshold FLOAT Minimum edge required to place sell orders (default: 0.0)
--sell-below FLOAT     Automatically sell positions with prediction below this percentage
--min-prediction FLOAT Only bid on opportunities with prediction at or above this value
--amount FLOAT         Amount to bid in USDC (default: 1.0)
--dry-run              Test without placing actual orders
--weighted-selection   Use weighted probability selection instead of always choosing the best opportunity
--show-positions       Show all current positions when running
--show-active-positions Show positions for active market when running
```

### Auto-Bidder Options

The Auto-Bidder identifies and places buy orders. Key options include:

```
--threshold FLOAT      Minimum statistical edge required (default: 0.0)
--min-prediction FLOAT Only consider opportunities with prediction above this value
--amount FLOAT         Amount to bid in USDC (default: 1.0)
--weighted-selection   Use weighted selection instead of always choosing the best opportunity
--dry-run              Find opportunities but don't place actual orders
```

### Position Seller Options

The Position Seller identifies and sells positions. Key options include:

```
--threshold FLOAT      Minimum statistical edge required for selling (default: 0.0)
--sell-below FLOAT     Sell positions with prediction below this percentage
--auto-sell            Automatically execute sell orders (otherwise just show recommendations)
--dry-run              Show what would be sold without executing actual orders
```

## Running in Production

For running in production as a background service:

```bash
# Run as a background service
nohup python -m src.scheduler.scheduler --buy-threshold 1.0 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 5.0 --weighted-selection --interval 30 > /dev/null 2>&1 &

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
