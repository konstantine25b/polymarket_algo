# Tweet Scheduler

A tool for automating the tweet fetching and prediction processes for Polymarket.

## Overview

This module provides an automated scheduler that periodically:

1. Fetches Elon Musk's tweets and stores them in the database
2. Runs the Polymarket predictor to update predictions
3. Runs the Market Prediction Comparison Tool to identify trading opportunities

## Features

- **Configurable interval**: Set how often to run the process (default: 20 minutes)
- **Selective execution**: Run only tweet fetching or only predictions
- **Smart incremental fetching**: Uses advanced incremental fetching strategy by default to ensure continuous tweet collection
- **Logging**: Comprehensive logging to file and console
- **One-time execution**: Option to run once and exit
- **Quiet mode**: Reduce output verbosity
- **Market comparison**: Compares prediction data against actual Polymarket order book data
- **Trading opportunities**: Identifies potential trading opportunities with customizable threshold
- **Enhanced visualization**: Optional detailed dashboard showing multiple comparison charts

## Command-Line Usage

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

# Change the maximum number of tweets to fetch
python -m src.scheduler --max-tweets 100

# Disable debug mode for tweet fetching
python -m src.scheduler --no-debug

# Run in quiet mode with less output
python -m src.scheduler --quiet

# Customize incremental fetching parameters
python -m src.scheduler --initial-batch 60 --max-batch 300

# Disable incremental fetching (not recommended)
python -m src.scheduler --no-incremental

# Don't run the market comparison after predictions
python -m src.scheduler --no-stats

# Set a minimum threshold for trading opportunities (e.g., 3%)
python -m src.scheduler --threshold 3.0

# Use enhanced visualization for market comparison
python -m src.scheduler --enhanced-viz

# Combine multiple options
python -m src.scheduler --interval 15 --max-tweets 50 --quiet --threshold 5.0 --enhanced-viz
```

## Command-Line Options

- `--interval`: Set the interval between runs in minutes (default: 20)
- `--tweets-only`: Only run the tweet fetching job
- `--predictions-only`: Only run the prediction job
- `--max-tweets`: Maximum number of tweets to fetch (default: 40)
- `--no-debug`: Disable debug mode for tweet fetching
- `--run-once`: Run jobs once and exit
- `--quiet`: Reduce output verbosity
- `--no-incremental`: Disable incremental fetching (not recommended)
- `--initial-batch`: Initial batch size for incremental fetching (default: 40)
- `--max-batch`: Maximum batch size for incremental fetching (default: 200)
- `--no-prophet`: Disable Prophet algorithm for predictions (use standard algorithm instead)
- `--no-stats`: Don't run the market comparison after predictions
- `--threshold`: Minimum opportunity percentage for trading recommendations (default: 0.0)
- `--enhanced-viz`: Generate enhanced visualization dashboard with detailed charts

## Smart Incremental Fetching

The scheduler now uses an intelligent incremental fetching strategy by default, which:

1. Starts with a small batch size (default: 40 tweets)
2. Checks if this batch overlaps with your existing database
3. If not found, gradually increases the batch size and tries again
4. Ensures no gaps in your tweet timeline

This approach provides several benefits:

- Ensures continuous, gap-free tweet collection
- Minimizes API costs by adapting to the actual number of new tweets
- Handles cases where many tweets are posted between scheduled runs
- Automatically adjusts batch sizes to maintain data continuity

You can customize the incremental fetching parameters using the `--initial-batch` and
`--max-batch` options, or disable it entirely with `--no-incremental` (though this is not recommended).

## Market Prediction Comparison

After running predictions, the scheduler automatically executes the Market Prediction Comparison Tool, which:

1. Compares Prophet model predictions with actual Polymarket order book data
2. Calculates differences between predicted and actual market prices
3. Identifies potential trading opportunities based on these differences
4. Generates visualizations comparing predictions with market data
5. Provides specific trading recommendations with prices

Example output:

```
Comparison Table:
           Range  Prediction (%)  Market (%)  Bid (%)  Ask (%)  Difference (%)  Opportunity (%)  Adj. Opportunity (0.0%)
        150–174          95.58       89.50    89.00    90.00           5.58            5.58                     5.58
        175–199           3.65        9.50     9.00    10.00          -6.35            6.35                     6.35
        200–224           0.48        0.15     0.00     0.50          -0.02            0.02                     0.02
        225–249           0.14        0.00     0.00     0.50          -0.36            0.36                     0.36
...

Best Trading Opportunity:
Range: 175–199
Prediction: 3.65%
Market: 9.5%
Bid: 9.0%
Ask: 10.0%
Difference: -6.35%
Opportunity: 6.35%
Adjusted Opportunity: 6.35%
Recommendation: SELL 175–199 at 9.0% (prediction: 3.65%)
Edge: 6.35% after 0.0% threshold
```

To customize the market comparison:

- `--threshold`: Set the minimum opportunity percentage (default: 0.0%, shows all opportunities)
- `--enhanced-viz`: Generate a comprehensive dashboard with multiple charts
- `--no-stats`: Skip the market comparison entirely

## Logs

The scheduler writes logs to both the console and a log file:

- **Log file location**: `src/logs/scheduler.log`
- **Log format**: `timestamp - name - level - message`

## Running as a Background Service

To run the scheduler as a background service (e.g., on a server), you can use:

```bash
nohup python -m src.scheduler > /dev/null 2>&1 &
```

Or with custom options:

```bash
nohup python -m src.scheduler --interval 10 --quiet --threshold 3.0 > /dev/null 2>&1 &
```

To stop the scheduler running in the background:

```bash
# Find the process ID
ps aux | grep src.scheduler

# Kill the process
kill <process_id>
```

## Implementation Details

The scheduler uses Python's `subprocess` module to run the tweet fetching, prediction, and market comparison scripts as separate processes. This ensures that any failures in one process don't affect the others.

Each process is monitored, and failures are logged. If the tweet fetching process fails, the prediction process is still attempted (unless configured otherwise). If the prediction process succeeds, the market comparison is then executed.

## Related Modules

- **src.apify.get_elon_tweets**: Module for fetching tweets
- **src.polymarket_predictor**: Module for running predictions
- **src.bidding_decision.stats**: Module for comparing predictions with market data
